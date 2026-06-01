# 股票交易策略回测系统

Streamlit Cloud deployment package for `backtest_app_5.py`.

## Deploy on Streamlit Cloud

1. Push this folder to a GitHub repository.
2. Open Streamlit Community Cloud and create a new app.
3. Select the repository and branch.
4. Set the main file path:

```text
backtest_app_5.py
```

5. Add the TickFlow key in Streamlit Cloud secrets:

```toml
TICKFLOW_API_KEY = "your_tickflow_key"
```

The app also supports local environment variables with the same name.

## Local Run

```powershell
pip install -r requirements.txt
streamlit run backtest_app_5.py
```

## Notes

- Do not commit `.streamlit/secrets.toml`.
- Generated PNG/HTML files and `yfinance_cache/` are intentionally ignored.
- If TickFlow is not configured, the app will attempt to use TickFlow free mode and then fallback data sources where available.
