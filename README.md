# BookMyShow Scraper

A Python scraper for extracting movie showtime data, seat availability, and cinema information from BookMyShow India.

## 🎬 Features

- **Movie Search**: Search for movies by name and get detailed information
- **Multi-format Support**: Extracts data for all available formats (2D, 3D, IMAX, etc.) and languages
- **Cinema Information**: Gets top 5 cinemas for each movie format
- **Seat Availability**: Real-time seat availability data for each showtime
- **JSON Export**: Exports all data to a structured JSON format

## 📋 Prerequisites

- Python 3.7+
- Chrome browser (for zendriver automation)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bookmyshow_scraper
   ```

2. **Install required packages**
   ```bash
   pip install zendriver cloudscraper beautifulsoup4
   ```

   Or create a requirements.txt file:
   ```bash
   pip install -r requirements.txt
   ```

## 📦 Dependencies

- `zendriver` - Browser automation for web scraping
- `cloudscraper` - HTTP client with anti-bot protection
- `beautifulsoup4` - HTML parsing
- `asyncio` - Asynchronous programming support
- `json` - JSON data handling
- `re` - Regular expressions
- `time` - Time delays and timing

## 🎯 Usage

1. **Basic Usage**
   ```python
   python main.py
   ```

2. **Customize the search**
   
   Edit the variables at the bottom of `main.py`:
   ```python
   city = "vadodara"  # Change to your city
   movie_name = "how to train your dragon"  # Change to your movie
   ```

3. **Supported Cities**
   - Use the city slug as it appears in BookMyShow URLs
   - Examples: `mumbai`, `delhi`, `bangalore`, `pune`, `vadodara`, etc.

## 📊 Output Format

The scraper generates an `output.json` file with the following structure:

```json
[
  {
    "movie_type": "2D",
    "language": "English",
    "cinemas": [
      {
        "name": "PVR Cinemas",
        "showtimes": [
          {
            "time": "10:30 AM",
            "available_seats": 45,
            "blocked_seats": 15,
            "total_seats": 60
          }
        ]
      }
    ]
  }
]
```

### Data Fields Explanation

- **movie_type**: Format dimension (2D, 3D, IMAX, etc.)
- **language**: Movie language (English, Hindi, etc.)
- **cinemas**: List of cinema complexes
- **showtimes**: Available show timings
- **available_seats**: Currently bookable seats
- **blocked_seats**: Sold/unavailable seats
- **total_seats**: Total capacity

## 🔧 Configuration

### Browser Settings
The scraper runs in headless mode by default. To see the browser in action:
```python
browser = await zd.start(headless=False)  # Change to False
```

### Timing Adjustments
Modify delays if you experience issues:
```python
time.sleep(3)  # Increase for slower connections
```

### Cinema Limit
Change the number of cinemas to scrape:
```python
cinema_containers = soup.find_all("div", class_="sc-e8nk8f-3 hStBrg")[:5]  # Change 5 to desired number
```