import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import logging
import time
import re
from urllib.error import HTTPError
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://groww.in/mutual-funds/filter?q=&fundSize=&pageNo={}&sortBy=0"
DELAY_SECONDS = 3  # Increased to 3 seconds to reduce rate limiting
MAX_FUNDS = 200    # Limit to 200 schemes as per user requirement

def fetch_page(url):
    """Fetch a webpage and return its BeautifulSoup object with error handling."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully fetched {url}")
        soup = BeautifulSoup(response.content, 'html.parser')
        logger.debug(f"Page content snippet: {str(soup)[:500]}")
        return soup
    except (requests.RequestException, HTTPError) as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None

def fetch_amfi_nav(scheme_code, start_date='2024-05-05', end_date='2025-05-05'):
    """Fetch historical NAV data from AMFI as a fallback."""
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    try:
        df = pd.read_csv(url, sep=';', skiprows=1, names=['Scheme Code', 'ISIN', 'Name', 'NAV', 'Date'])
        df = df[df['Scheme Code'] == int(scheme_code)]
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')
        df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        nav_data = df[['Date', 'NAV']].to_dict(orient='records')
        formatted_data = [{'date': str(entry['Date'])[:10], 'nav': float(entry['NAV'])} for entry in nav_data]
        logger.info(f"Fetched {len(formatted_data)} NAV entries from AMFI for scheme {scheme_code}")
        return formatted_data
    except (pd.errors.EmptyDataError, requests.RequestException, ValueError) as e:
        logger.error(f"Failed to fetch AMFI NAV for scheme {scheme_code}: {e}")
        return []

def extract_historical_nav(scheme_code, months=12):
    """Fetch historical NAV data for a scheme over a specified number of months."""
    if not scheme_code or pd.isna(scheme_code):
        logger.warning(f"No scheme code provided for historical NAV extraction")
        return []

    url = f"https://groww.in/v1/api/data/mf/web/v1/scheme/{scheme_code}/graph?benchmark=false&months={months}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        data = response.json()

        nav_data = data.get('folio', {}).get('data', [])
        if not nav_data:
            logger.warning(f"No NAV data found in response for scheme {scheme_code}")
            return []

        formatted_data = []
        for entry in nav_data:
            if isinstance(entry, list) and len(entry) == 2:
                try:
                    timestamp_ms = entry[0]
                    nav_value = float(entry[1])
                    timestamp_s = timestamp_ms / 1000
                    date_str = datetime.utcfromtimestamp(timestamp_s).strftime('%Y-%m-%d')
                    formatted_data.append({'date': date_str, 'nav': nav_value})
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid NAV entry for scheme {scheme_code}: {entry}, error: {e}")
                    continue
            else:
                logger.warning(f"Unexpected NAV entry format for scheme {scheme_code}: {entry}")
                continue

        logger.info(f"Fetched {len(formatted_data)} NAV entries from Groww for scheme {scheme_code}")
        return formatted_data

    except (requests.RequestException, ValueError, KeyError) as e:
        logger.warning(f"Failed to fetch historical NAV from Groww for scheme {scheme_code}: {e}")

    logger.info(f"Falling back to AMFI for scheme {scheme_code}")
    return fetch_amfi_nav(scheme_code)

def extract_top_holdings(scheme_code, fund_link):
    """Scrape top holdings for a mutual fund scheme directly from the fund page."""
    if not scheme_code or pd.isna(scheme_code) or not fund_link:
        logger.warning(f"Invalid scheme code or fund link for top holdings extraction: scheme_code={scheme_code}, fund_link={fund_link}")
        return []

    logger.info(f"Scraping top holdings from fund page for scheme {scheme_code}: {fund_link}")
    soup = fetch_page(fund_link)
    if not soup:
        logger.warning(f"Failed to fetch fund page for scheme {scheme_code}")
        return []

    top_holdings = []
    # Find the holdings table using the class 'holdings101Table'
    table = soup.find('table', class_='holdings101Table')
    if not table:
        logger.warning(f"Holdings table not found on fund page for scheme {scheme_code}")
        return []

    # Extract rows from the table body (skip header)
    rows = table.find('tbody').find_all('tr')[:5] if table.find('tbody') else table.find_all('tr')[1:6]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 4:  # Expecting 4 columns: Name, Sector, Instrument, Assets
            # Extract company name from the first column
            company_elem = cols[0].find('div', class_='pc543Links') or cols[0]
            company = company_elem.text.strip() if company_elem else 'Unknown'
            # Extract percentage from the fourth column
            percentage = cols[3].text.strip().replace('%', '')
            try:
                percentage = float(percentage)
            except ValueError:
                logger.warning(f"Invalid percentage value for holding in scheme {scheme_code}: {percentage}")
                percentage = 0.0
            top_holdings.append({'company': company, 'percentage': percentage})

    if not top_holdings:
        logger.warning(f"No top holdings extracted from fund page for scheme {scheme_code}")
    else:
        logger.info(f"Fetched {len(top_holdings)} top holdings for scheme {scheme_code} via web scraping")

    return top_holdings

def extract_fund_overview(page_no):
    """Extract overview data (name, risk, type, returns, links) from a page."""
    url = BASE_URL.format(page_no)
    soup = fetch_page(url)
    if not soup:
        return []

    fund_cards = soup.find_all('div', class_='contentPrimary f22LH34 f22Mb4 truncate bodyBaseHeavy')
    if not fund_cards:
        logger.warning(f"No fund cards found on page {page_no + 1}")
        return []

    funds_data = []
    for card in fund_cards:
        name_elem = card
        name = name_elem.text.strip() if name_elem else ""

        parent = card.find_parent('a', class_='pos-rel f22Link')
        if not parent:
            continue

        risk_type_elements = parent.find_all('div', class_='contentSecondary f22Ls2 contentTertiary bodySmallHeavy')
        risk = risk_type_elements[0].text.strip() if len(risk_type_elements) > 0 else ""
        type_ = risk_type_elements[1].text.strip() if len(risk_type_elements) > 1 else ""

        return_elements = parent.find_all('div', class_='contentPrimary center-align f22Mb4 bodyBaseHeavy')
        returns = [elem.text.strip() for elem in return_elements[:3]]
        while len(returns) < 3:
            returns.append("NA")

        link = parent.get('href', '')
        if link and not link.startswith('http'):
            link = f"https://groww.in{link}"

        if name and link:
            funds_data.append({
                'name': name,
                'risk': risk,
                'type': type_,
                'returns': returns,
                'link': link
            })

    logger.info(f"Fetched page {page_no + 1}, found {len(funds_data)} funds")
    return funds_data

def extract_detailed_fund_data(url):
    """Extract detailed data (AUM, NAV, minimum investment, minimum SIP investment, rating, expense ratio, exit load)."""
    soup = fetch_page(url)
    if not soup:
        return [np.nan] * 7

    aum = np.nan
    all_elements = soup.find_all(['td', 'div', 'span'], class_=['bodyLarge', 'bodyLargeHeavy', 'contentPrimary'])
    for elem in all_elements:
        previous = elem.find_previous_sibling(['td', 'div', 'span'], class_=['contentSecondary', 'bodyLarge'])
        if previous and 'Fund size' in previous.text:
            text = elem.text.strip()
            try:
                aum = float(text.replace('₹', '').replace(',', '').replace('Cr', ''))
                break
            except ValueError:
                continue

    nav = np.nan
    for elem in all_elements:
        previous = elem.find_previous_sibling(['td', 'div', 'span'], class_=['contentSecondary', 'bodyLarge'])
        if previous and 'NAV' in previous.text:
            text = elem.text.strip()
            try:
                nav = float(text.replace('₹', '').replace(',', ''))
                break
            except ValueError:
                continue

    minimum = np.nan
    minimum_sip = np.nan
    min_elements = soup.find_all('td', class_='bodyLargeHeavy')
    for elem in min_elements:
        text = elem.text.strip()
        parent = elem.find_previous_sibling('td', class_='contentSecondary bodyLarge')
        if parent and 'Min. for 1st investment' in parent.text:
            try:
                minimum = float(text.replace('₹', '').replace(',', ''))
                break
            except ValueError:
                continue
    for elem in min_elements:
        text = elem.text.strip()
        parent = elem.find_previous_sibling('td', class_='contentSecondary bodyLarge')
        if parent and 'Min. for SIP' in parent.text:
            try:
                minimum_sip = float(text.replace('₹', '').replace(',', ''))
                break
            except ValueError:
                continue
    # If minimum wasn't found, fall back to SIP amount for minimum (existing logic)
    if np.isnan(minimum):
        minimum = minimum_sip

    rating = np.nan
    rating_elements = soup.find_all('td', class_='fd12Cell valign-wrapper contentPrimary fd12Ratings bodyLargeHeavy')
    for elem in rating_elements:
        text = elem.text.strip()
        if text == 'NA':
            rating = np.nan
        else:
            try:
                rating = float(text)
                break
            except ValueError:
                continue

    exit_load = np.nan
    exit_load_elements = soup.find_all('p', class_='bodyLarge')
    for elem in exit_load_elements:
        text = elem.text.strip()
        if 'Exit load' in text:
            if 'No exit load' in text or '0%' in text:
                exit_load = 0.0
                break
            match = re.search(r'(\d+\.\d+)%', text)
            if match:
                try:
                    exit_load = float(match.group(1))
                    break
                except ValueError:
                    continue

    expense_ratio = np.nan
    for elem in exit_load_elements:
        text = elem.text.strip()
        if 'Expense ratio' in text:
            match = re.search(r'(\d+\.\d+)%', text)
            if match:
                try:
                    expense_ratio = float(match.group(1))
                    break
                except ValueError:
                    continue

    return [aum, nav, minimum, minimum_sip, rating, expense_ratio, exit_load]

def extract_scheme_code(url):
    """Extract scheme_code from a fund page's script tags."""
    soup = fetch_page(url)
    if not soup:
        return np.nan
    scripts = soup.find_all('script')
    for script in scripts:
        match = re.search(r'"scheme_code":"(\d+)"', str(script))
        if match:
            return match.group(1)
    return np.nan

def extract_portfolio_stats(scheme_code, fund_type, retries=3, retry_delay=5):
    """Fetch and extract portfolio statistics, asset allocation, and equity sector allocation from the Groww API."""
    if not scheme_code or pd.isna(scheme_code):
        logger.warning(f"No scheme code provided for portfolio stats extraction")
        return {
            'pe': np.nan,
            'pb': np.nan,
            'debt_per': np.nan,
            'equity_per': np.nan,
            'average_maturity': np.nan,
            'yield_to_maturity': np.nan,
            'asset_allocation': {'equity': np.nan, 'debt': np.nan, 'cash': np.nan, 'total_aum': np.nan},
            'sector_allocation': [],
            'equity_aum': np.nan
        }

    url = f"https://groww.in/v1/api/data/mf/web/v1/scheme/portfolio/{scheme_code}/stats"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Extract portfolio stats (existing logic)
            stats = {
                'pe': data.get('pe', np.nan),
                'pb': data.get('pb', np.nan),
                'debt_per': data.get('debt_per', np.nan),
                'equity_per': data.get('equity_per', np.nan),
                'average_maturity': data.get('average_maturity', np.nan),
                'yield_to_maturity': data.get('yield_to_maturity', np.nan)
            }

            if fund_type == 'Commodities':
                stats['pe'] = np.nan
                stats['pb'] = np.nan
                stats['debt_per'] = 0
                stats['equity_per'] = 0
            if fund_type != 'Hybrid':
                stats['average_maturity'] = np.nan
                stats['yield_to_maturity'] = np.nan
            if fund_type == 'Hybrid':
                debt = stats['debt_per'] if not pd.isna(stats['debt_per']) else 0
                equity = stats['equity_per'] if not pd.isna(stats['equity_per']) else 0
                total = debt + equity
                if total > 0:
                    stats['debt_per'] = (debt / total) * 100
                    stats['equity_per'] = (equity / total) * 100
                else:
                    stats['debt_per'] = np.nan
                    stats['equity_per'] = np.nan

            # Extract asset allocation (Equity/Debt/Cash split)
            asset_breakdown = data.get('asset_allocation', {})
            asset_allocation = {
                'equity': float(asset_breakdown.get('equity', 0)),
                'debt': float(asset_breakdown.get('debt', 0)),
                'cash': float(asset_breakdown.get('cash', 0)),
                'total_aum': float(data.get('aum', np.nan))
            }

            # Extract equity sector allocation
            sector_breakdown = data.get('equity_sector_per', {})
            sector_allocation = []
            for sector_name, percentage in sector_breakdown.items():
                sector_allocation.append({'sector': sector_name, 'percentage': float(percentage)})
            # Sort sectors by percentage in descending order and limit to top 4
            sector_allocation = sorted(sector_allocation, key=lambda x: x['percentage'], reverse=True)[:4]

            # Calculate equity AUM
            if not np.isnan(asset_allocation['total_aum']):
                equity_aum = (asset_allocation['equity'] / 100) * asset_allocation['total_aum']
            else:
                equity_aum = np.nan

            stats.update({
                'asset_allocation': asset_allocation,
                'sector_allocation': sector_allocation,
                'equity_aum': equity_aum
            })

            logger.info(f"Fetched portfolio stats and holding analysis for scheme {scheme_code}")
            time.sleep(1)  # Add a 1-second delay after a successful request
            return stats

        except (ValueError, KeyError, requests.RequestException) as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} - Failed to fetch portfolio stats for scheme {scheme_code}: {e}")
            if attempt < retries - 1:
                logger.info(f"Retrying after {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All retry attempts failed for scheme {scheme_code}")
                return {
                    'pe': np.nan,
                    'pb': np.nan,
                    'debt_per': np.nan,
                    'equity_per': np.nan,
                    'average_maturity': np.nan,
                    'yield_to_maturity': np.nan,
                    'asset_allocation': {'equity': np.nan, 'debt': np.nan, 'cash': np.nan, 'total_aum': np.nan},
                    'sector_allocation': [],
                    'equity_aum': np.nan
                }

def process_returns(returns_list, expected_count):
    """Process returns list into 1Y, 3Y, 5Y lists, ensuring length matches expected_count."""
    one_year, three_year, five_year = [], [], []
    for returns in returns_list:
        one_year_val = returns[0] if returns[0] != 'NA' else np.nan
        three_year_val = returns[1] if returns[1] != 'NA' else np.nan
        five_year_val = returns[2] if returns[2] != 'NA' else np.nan
        one_year.append(float(one_year_val.rstrip('%')) if isinstance(one_year_val, str) and one_year_val.endswith('%') else one_year_val)
        three_year.append(float(three_year_val.rstrip('%')) if isinstance(three_year_val, str) and three_year_val.endswith('%') else three_year_val)
        five_year.append(float(five_year_val.rstrip('%')) if isinstance(five_year_val, str) and five_year_val.endswith('%') else five_year_val)

    for lst in [one_year, three_year, five_year]:
        while len(lst) < expected_count:
            lst.append(np.nan)

    return one_year, three_year, five_year

def normalize_link(link):
    """Normalize the link by extracting the core slug to prevent duplicates."""
    slug = link.split('mutual-funds/')[-1].split('?')[0]
    suffixes = ['-fund', '-direct', '-growth', '-plan', '-scheme']
    for suffix in suffixes:
        slug = slug.replace(suffix, '')
    slug = '-'.join(filter(None, slug.split('-')))
    return slug

def main():
    logger.info("Starting data extraction process")

    all_funds = []
    page_no = 0
    seen = set()
    while len(all_funds) < MAX_FUNDS:
        funds_data = extract_fund_overview(page_no)
        if not funds_data:
            logger.warning(f"No more funds to fetch after page {page_no + 1}")
            break

        for fund in funds_data:
            key = (fund['name'].strip(), normalize_link(fund['link']))
            if key not in seen:
                seen.add(key)
                all_funds.append(fund)
                if len(all_funds) >= MAX_FUNDS:
                    break

        page_no += 1
        time.sleep(DELAY_SECONDS)

    num_funds = len(all_funds)
    logger.info(f"Processing {num_funds} funds after deduplication")

    all_names = [fund['name'] for fund in all_funds]
    all_risks = [fund['risk'] for fund in all_funds]
    all_types = [fund['type'] for fund in all_funds]
    all_returns = [fund['returns'] for fund in all_funds]
    all_links = [fund['link'].strip().split('?')[0] for fund in all_funds]

    one_year_returns, three_year_returns, five_year_returns = process_returns(all_returns, num_funds)

    aum_list, nav_list, min_inv_list, min_sip_list, rating_list, exp_ratio_list, exit_load_list = [], [], [], [], [], [], []
    scheme_codes = []
    historical_navs = []
    top_holdings_list = []
    # Lists for holding analysis data
    asset_allocations = []
    sector_allocations = []
    equity_aums = []

    for fund in all_funds:
        link = fund['link']
        aum, nav, minimum, minimum_sip, rating, exp_ratio, exit_load = extract_detailed_fund_data(link)
        aum_list.append(aum)
        nav_list.append(nav)
        min_inv_list.append(minimum)
        min_sip_list.append(minimum_sip)
        rating_list.append(rating)
        exp_ratio_list.append(exp_ratio)
        exit_load_list.append(exit_load)
        scheme_code = extract_scheme_code(link)
        scheme_codes.append(scheme_code)

        nav_data = extract_historical_nav(scheme_code, months=12)
        historical_navs.append(nav_data)

        top_holdings = extract_top_holdings(scheme_code, fund_link=link)
        top_holdings_list.append(top_holdings)

        # Extract portfolio stats and holding analysis
        stats = extract_portfolio_stats(scheme_code, fund['type'])
        asset_allocations.append(stats['asset_allocation'])
        sector_allocations.append(stats['sector_allocation'])
        equity_aums.append(stats['equity_aum'])

        time.sleep(DELAY_SECONDS)

    analysis = {
        'name': all_names,
        'aum': aum_list,
        'nav': nav_list,
        'exit_load': exit_load_list,
        'rating': rating_list,
        'minimum_investment': min_inv_list,
        'minimum_sip_investment': min_sip_list,
        'pe': [stats['pe'] for stats in [extract_portfolio_stats(code, fund['type']) for code, fund in zip(scheme_codes, all_funds)]],
        'pb': [stats['pb'] for stats in [extract_portfolio_stats(code, fund['type']) for code, fund in zip(scheme_codes, all_funds)]],
        'debt_per': [stats['debt_per'] for stats in [extract_portfolio_stats(code, fund['type']) for code, fund in zip(scheme_codes, all_funds)]],
        'equity_per': [stats['equity_per'] for stats in [extract_portfolio_stats(code, fund['type']) for code, fund in zip(scheme_codes, all_funds)]],
        'average_maturity': [stats['average_maturity'] for stats in [extract_portfolio_stats(code, fund['type']) for code, fund in zip(scheme_codes, all_funds)]],
        'yield_to_maturity': [stats['yield_to_maturity'] for stats in [extract_portfolio_stats(code, fund['type']) for code, fund in zip(scheme_codes, all_funds)]],
        'risk': all_risks,
        'type': all_types,
        'one_year_return': one_year_returns,
        'three_year_return': three_year_returns,
        'five_year_return': five_year_returns,
        'link': all_links,
        'historical_nav': historical_navs,
        'top_holdings': top_holdings_list,
        # Fields for holding analysis
        'asset_allocation': asset_allocations,
        'sector_allocation': sector_allocations,
        'equity_aum': equity_aums
    }

    logger.info("Lengths of all lists in analysis dictionary:")
    for key, value in analysis.items():
        logger.info(f"{key}: {len(value)}")

    try:
        analysis_df = pd.DataFrame(analysis)
        analysis_df.to_excel("raw_data.xlsx", index=False)
        logger.info("Raw data for 200 schemes has been extracted and saved to raw_data.xlsx")
        logger.info(f"Total number of schemes extracted: {len(analysis_df)}")
    except Exception as e:
        logger.error(f"Failed to create DataFrame or export to Excel: {e}")

if __name__ == "__main__":
    main()