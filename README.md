
# Mutual Fund Scraping and Analysis Project

## Overview
This project involves scraping mutual fund data from Groww.in, processing it, and presenting insights through an interactive dashboard with a future return prediction calculator. It collects data for 200 mutual funds, including AUM, NAV, returns, risk metrics (alpha, beta, Sharpe), top holdings, and sector allocations. The dashboard, developed using Streamlit and Plotly, provides visualizations such as PE vs PB comparisons, risk vs return scatter plots, and a returns heatmap with a red-to-blue color scale. The prediction calculator leverages historical NAV data and Scikit-Learn regression models to forecast future returns based on user inputs like time horizon and risk adjustments.

## Features
- **Data Scraping**: Fetches mutual fund data from Groww.in using Python, BeautifulSoup, and Playwright for dynamic content handling.
- **Data Processing**: Cleans and preprocesses data, addressing missing values, inconsistencies, and formatting issues.
- **Interactive Dashboard**: Displays fund performance, risk metrics, and portfolio breakdowns with user-friendly filters.
- **Prediction Calculator**: Forecasts future returns using regression models, allowing users to adjust time horizons and risk levels.
- **Advanced Visualizations**: Includes dynamic charts like returns heatmaps, scatter plots, and bar charts for portfolio allocations.
- **Export Functionality**: Saves processed data to `raw_data.xlsx` for further analysis or reporting.

## Requirements
- Python 3.8 or higher
- Libraries: `requests`, `beautifulsoup4`, `playwright`, `pandas`, `numpy`, `streamlit`, `plotly`, `scikit-learn`
- Install dependencies using:
  ```
  pip install -r requirements.txt
  ```
- For Playwright browser binaries:
  ```
  playwright install
  ```

## Setup
1. Clone the repository to your local machine:
   ```
   git clone <https://github.com/SYED-YAHEYA/Mutual-fund-analysis-dashboard>
   cd mutual-fund-scraping-project
   ```
2. Install the required Python libraries as listed in `requirements.txt`.
3. Install Playwright dependencies for scraping dynamic content.
4. Ensure an active internet connection for data scraping from Groww.in.

## Usage
1. **Scrape Data**:
   Execute the scraping script to collect mutual fund data:
   ```
   python extraction.py
   ```
   This script scrapes data for 200 funds, processes it, and saves the output to `raw_data.xlsx`.

2. **Launch the Dashboard**:
   Run the Streamlit app to explore the data and use the prediction calculator:
   ```
   streamlit run dashboard.py
   ```
   The dashboard will be accessible at `http://localhost:8501` in your browser.

3. **Interact with the Dashboard**:
   - Use dropdowns and sliders to filter funds by type, risk, or performance metrics.
   - Explore visualizations such as PE vs PB scatter plots, risk vs return charts, and sector allocation bar graphs.
   - Access the prediction calculator to input a time horizon (e.g., 1-5 years) and risk adjustment, then view forecasted returns.
   - Analyze trends with the returns heatmap, which uses a red-to-blue color scale to highlight performance.

## Project Structure
- `extraction.py`: Handles data scraping, cleaning, and processing from Groww.in.
- `dashboard.py`: Contains the Streamlit app code for the dashboard and prediction calculator.
- `raw_data.xlsx`: Output Excel file with scraped data, including fund details, historical NAVs, and top holdings.
- `requirements.txt`: Lists all necessary Python libraries for the project.

## Data Sources
- Mutual fund data is sourced from Groww.in using a combination of API calls and web scraping.
- Historical NAV data is used for trend analysis and return predictions.

## Technical Details
- **Scraping**: Utilizes `requests` and `BeautifulSoup` for static content, with Playwright for JavaScript-rendered data like advanced ratios.
- **Data Processing**: Employs Pandas and NumPy for cleaning, feature engineering, and handling missing values.
- **Prediction Model**: Implements Scikit-Learn regression models (e.g., Linear Regression) on historical NAV data to forecast returns.
- **Visualizations**: Leverages Plotly for interactive charts, ensuring dynamic user interaction and clear insights.

## Notes
- Ensure compliance with Groww.in’s terms of service when scraping data.
- Rate limiting and error handling are implemented to prevent request blocks and ensure scraping stability.
- Prediction accuracy depends on historical data quality and market volatility; results should be used as insights, not guarantees.
- The dashboard is locally hosted via Streamlit; for public deployment, consider hosting on Streamlit Community Cloud or similar platforms.

## Future Improvements
- Integrate real-time data updates using a backend API for live mutual fund metrics.
- Enhance the prediction calculator with advanced models like XGBoost or LSTM for better accuracy.
- Add export options for visualizations (e.g., PNG, PDF) and more interactive filters (e.g., by fund manager).
- Implement user authentication and personalized watchlists for a more tailored experience.

## Acknowledgments
- Data sourced from Groww.in.
- Built using open-source libraries: Streamlit, Plotly, Scikit-Learn, Pandas, and BeautifulSoup.
- Inspired by the need for accessible financial analysis tools for retail investors.

## Contact
For questions or contributions, reach out to SYED YAHEYA at syedyaheya16@gmail.com 
