# LimitOrderBook Trading Engine

A Django-based backend engine for managing a limit order book, designed for algorithmic trading platforms or as a backend for exchanges. It supports order matching, trade recording, and candlestick (K-line) chart generation.

## Features
- Limit and market order matching
- Trade recording and OHLC data extraction
- K-line (candlestick) chart generation using pandas and matplotlib
- Django admin interface for management

## Requirements
- Python 3.8+
- Django 4.0.6
- Django REST Framework
- pandas
- matplotlib
- python-dotenv

## Installation
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd TradeEngine
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (optional):
   - Create a `.env` file in the project root if needed.
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Usage
- Access the Django admin interface at `http://localhost:8000/admin/`.
- Core trading logic is implemented in `apps/orderbook/`.
- Trades and order book data are managed in-memory and can be visualized as K-line charts.

## Project Structure
```
TradeEngine/
├── apps/
│   └── orderbook/
│       ├── orderbook.py      # Main order book logic
│       ├── order.py         # Order data structure
│       ├── trade.py         # Trade recording and charting
│       └── ...
├── LimitOrderBook/
│   ├── settings.py          # Django settings
│   ├── urls.py              # URL configuration
│   └── ...
├── manage.py                # Django entry point
├── requirements.txt         # Python dependencies
└── ...
```

## Contributing
Contributions are welcome! Please open issues or submit pull requests for improvements.

## License
This project does not specify a license. Please add one if needed.

