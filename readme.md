# Geo-MMO City Builder ServerA game server for a Geo-MMO city builder powered by Copernicus land cover data and real-world exploration. 



A game server for a geospatially-aware MMO city builder powered by **Copernicus land cover data** and real-world exploration. Players build settlements on a hexagonal grid mapped to real-world locations, utilizing actual biome and terrain data.# Requirements

Python 3.9+

## 🌍 Features

# Create a .env file with API secrets

- **Real-world geospatial data** from Copernicus satellite imageryUse the .env.template file.
- **Hexagonal grid system** (H3) for efficient spatial operations
- **Biome-based resource economy** (trees, crops, water, etc.)
- **RESTful API** built with FastAPI
- **Player settlements** and resource management

## 🏗️ Architecture

```
ae-cassini-server-2025/
├── src/
│   ├── api/                 # FastAPI routes and endpoints
│   ├── copernicus/          # Copernicus satellite data integration
│   ├── database/            # Database models and connections
│   ├── game_objects/        # Core game models (Tile, Settlement, etc.)
│   ├── config.py            # Configuration management
│   └── main.py              # FastAPI app entry point
├── .env.template            # Environment variable template
├── requirements.txt         # Python dependencies
├── setup.ps1                # Setup script (Windows)
└── start.ps1                # Start server script (Windows)
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Copernicus Data Space account** (for API credentials)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ae-cassini-server-2025
   ```

2. **Run setup script (Windows)**
   ```powershell
   .\setup.ps1
   ```
   
   Or manually:
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # On Windows
   # source .venv/bin/activate  # On Linux/Mac
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.template .env
   ```
   
   Edit `.env` and add your Copernicus credentials:
   ```bash
   CLIENT_ID=your_copernicus_client_id
   CLIENT_SECRET=your_copernicus_client_secret
   ```
   
   Get credentials at: [Copernicus Data Space](https://dataspace.copernicus.eu/)

4. **Start the server**
   ```powershell
   .\start.ps1
   ```
   
   Or manually:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Access the API**
   - API Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/

## 📡 API Endpoints

### `GET /`
Health check endpoint.

**Response:**
```json
{
  "value": "This is a test."
}
```

### `GET /map/`
Fetch map data with biomes, settlements, and resources.

**Parameters:**
- `lat` (float, required): Latitude
- `lon` (float, required): Longitude  
- `range` (int, optional): Range in meters (default: 200)

**Response:**
```json
{
  "tiles": [
    {
      "hex_id": "8a1234567890abc",
      "biome": "Tree cover",
      "settlement": null,
      "boundary": [[lat, lon], ...]
    }
  ]
}
```

## 🎮 Game Objects

### Tile
Represents a hexagonal map tile with biome data.

### Settlement
Player-owned structures that produce resources.

### Resource
Game resources: `WHEAT`, `WOOD`, `STONE`, etc.

### Inventory
Manages resource quantities for settlements.

## 🛠️ Development

### Project Structure
- `src/api/` - API route handlers
- `src/copernicus/` - Copernicus data integration
- `src/game_objects/` - Core game models
- `src/database/` - Database layer (to be implemented)
- `src/config.py` - Centralized configuration

### Adding New Routes
Create routers in `src/api/` and register them in `src/main.py`:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/settlements", tags=["settlements"])

@router.get("/")
async def list_settlements():
    return {"settlements": []}
```

### Running Tests
```bash
pytest tests/
```

## 🌐 Data Sources

- **Copernicus Land Cover**: Global land cover classification at 10m resolution
- **EU-Hydro**: European hydrological network (rivers, lakes)
- **H3 Hexagons**: Uber's hexagonal hierarchical geospatial indexing system

## 📦 Dependencies

- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **H3** - Hexagonal spatial indexing
- **Rasterio** - Geospatial raster data
- **NumPy** - Numerical computing
- **Requests** - HTTP client
- **python-dotenv** - Environment variable management

## 🎯 Hackathon Goals

- [x] Project setup and structure
- [x] Copernicus data integration
- [x] Hexagonal grid system
- [ ] Player authentication
- [ ] Settlement placement and management
- [ ] Resource production system
- [ ] Player trading/economy
- [ ] WebSocket for real-time updates

## 📝 License

MIT License - feel free to use for your hackathon!

## 🤝 Contributing

This is a hackathon project. Feel free to fork and experiment!

## 🔗 Links

- [Copernicus Data Space](https://dataspace.copernicus.eu/)
- [H3 Spatial Index](https://h3geo.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
