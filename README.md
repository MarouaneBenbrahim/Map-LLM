# Manhattan Power Grid - Advanced Operations Center

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![SUMO](https://img.shields.io/badge/SUMO-1.15+-orange.svg)](https://eclipse.org/sumo/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **world-class, real-time power grid simulation system** integrating electrical power flow analysis, traffic management, electric vehicle simulation, and Vehicle-to-Grid (V2G) energy trading. Built for Manhattan's power infrastructure with advanced AI analytics and machine learning optimization.

![Manhattan Power Grid Dashboard](docs/images/dashboard-preview.png)

## 🌟 Key Features

### ⚡ **Advanced Power Grid Simulation**
- **PyPSA Integration**: Real-time DC power flow analysis
- **8 Substations**: Realistic Manhattan power infrastructure
- **Distribution Network**: 13.8kV primary and 480V secondary systems
- **Load Management**: Dynamic load balancing and optimization

### 🚗 **Intelligent Vehicle Simulation**
- **SUMO Integration**: Eclipse SUMO traffic simulation
- **Electric Vehicle Fleet**: Configurable EV percentage (0-100%)
- **Battery Management**: SOC-based routing and charging behavior
- **Real-time Tracking**: Live vehicle positions and battery states

### 🔋 **Vehicle-to-Grid (V2G) Technology**
- **Bidirectional Energy Flow**: EVs provide power back to grid
- **Emergency Response**: Automatic V2G activation during outages
- **Dynamic Pricing**: Market-based energy trading
- **Revenue Optimization**: Maximize EV owner earnings

### 🧠 **AI-Powered Analytics**
- **Machine Learning**: Demand prediction and optimization
- **Real-time Insights**: Grid performance analytics
- **Predictive Maintenance**: Failure prediction and prevention
- **Interactive Chatbot**: AI assistant for grid operations

### 🎮 **Professional Web Interface**
- **Glassmorphic Design**: Modern, premium UI/UX
- **Real-time Visualization**: Live map with Mapbox integration
- **Interactive Controls**: Comprehensive system management
- **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+ required
python --version  # Should be 3.8+

# SUMO Traffic Simulator
# Download from: https://eclipse.org/sumo/
# Add SUMO_HOME to your environment variables
```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/manhattan-power-grid.git
   cd manhattan-power-grid
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python main_complete_integration.py
   ```

6. **Open your browser**
   ```
   http://localhost:5000
   ```

## 📖 Usage Guide

### Basic Operations

1. **Start Vehicle Simulation**
   - Click "Start Vehicles" in the control panel
   - Configure EV percentage and battery ranges
   - Watch real-time vehicle movement and charging

2. **Test Power Grid Scenarios**
   - Click on substations to trigger failures
   - Observe traffic light responses (yellow = caution mode)
   - Monitor EV station impacts

3. **Enable V2G Emergency Response**
   - Fail a substation to create power deficit
   - Enable V2G for that substation
   - Watch high-SOC EVs provide backup power

4. **Use AI Analytics**
   - Access ML dashboard for insights
   - Chat with AI assistant for recommendations
   - Generate comprehensive system reports

### Configuration

#### EV Fleet Configuration
```python
# In the web interface
EV Percentage: 70%        # 70% of vehicles are electric
Battery SOC Range: 20-90% # Battery state of charge range
```

#### V2G Settings
```python
# Automatic V2G activation during emergencies
Emergency Threshold: 90%  # Substation loading threshold
V2G Power Rate: 250kW    # Power per vehicle
Market Price: $0.15/kWh  # Energy trading price
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │  Flask Backend  │    │  SUMO Simulator │
│                 │◄───┤                 │◄───┤                 │
│ • Mapbox Maps   │    │ • REST API      │    │ • Vehicle Sim   │
│ • Real-time UI  │    │ • WebSocket     │    │ • Traffic Mgmt  │
│ • Controls      │    │ • Data Processing│   │ • Route Planning│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PyPSA Grid    │    │   ML Engine     │    │   V2G Manager   │
│                 │    │                 │    │                 │
│ • Power Flow    │    │ • Demand Pred   │    │ • Energy Trade  │
│ • Load Analysis │    │ • Optimization  │    │ • Market Pricing │
│ • Grid Stability│    │ • AI Insights   │    │ • Route Planning │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### File Structure

```
manhattan-power-grid/
├── 📁 api/                    # API endpoints (organized)
├── 📁 core/                   # Core system components
│   ├── power_system.py        # PyPSA power grid
│   └── sumo_manager.py        # SUMO integration
├── 📁 static/                 # Web assets
│   ├── styles.css             # Main stylesheet
│   └── script.js              # Frontend JavaScript
├── 📁 data/                   # Data files and configs
├── 📁 docs/                   # Documentation
├── 📁 tests/                  # Test suites
├── main_complete_integration.py # Main application
├── integrated_backend.py      # Backend systems
├── v2g_manager.py             # V2G functionality
├── ml_engine.py               # ML analytics
├── ai_chatbot.py              # AI assistant
├── index.html                 # Main web interface
└── requirements.txt           # Dependencies
```

## 🔧 API Reference

### Core Endpoints

#### System Status
```http
GET /api/status
```
Returns complete system status including vehicles, grid state, and performance metrics.

#### Network State
```http
GET /api/network_state
```
Returns detailed network topology with real-time component states.

### Vehicle Management
```http
POST /api/sumo/start
Content-Type: application/json

{
  "vehicle_count": 10,
  "ev_percentage": 0.7,
  "battery_min_soc": 0.2,
  "battery_max_soc": 0.9
}
```

### Power Grid Control
```http
POST /api/fail/Times%20Square
```
Triggers substation failure simulation.

```http
POST /api/restore/Times%20Square
```
Restores failed substation.

### V2G Operations
```http
POST /api/v2g/enable/Times%20Square
```
Enables V2G for specified substation.

```http
GET /api/v2g/status
```
Returns V2G system status and active sessions.

### AI Analytics
```http
POST /api/ai/chat
Content-Type: application/json

{
  "message": "Analyze grid performance",
  "user_id": "operator_1"
}
```

## 🧪 Testing

### Run Test Suite
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# End-to-end tests
python -m pytest tests/e2e/

# All tests with coverage
python -m pytest --cov=. tests/
```

### Manual Testing Scenarios

1. **Basic Functionality**
   ```bash
   # Start system and verify all components load
   python main_complete_integration.py
   # Navigate to http://localhost:5000
   # Verify map loads and controls respond
   ```

2. **Vehicle Simulation**
   ```bash
   # Start SUMO simulation
   # Spawn 20 vehicles with 80% EVs
   # Verify vehicles appear on map and charge at stations
   ```

3. **Grid Failure Response**
   ```bash
   # Fail Times Square substation
   # Verify traffic lights turn yellow
   # Verify EV stations go offline
   # Enable V2G and verify emergency response
   ```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for all functions and classes
- Include unit tests for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Eclipse SUMO** - Traffic simulation framework
- **PyPSA** - Power system analysis library
- **Mapbox** - Interactive mapping platform
- **Flask** - Web framework
- **OpenAI** - AI integration capabilities

## 📞 Support

- 📧 **Email**: support@manhattan-power-grid.com
- 💬 **Discord**: [Join our community](https://discord.gg/manhattan-power-grid)
- 📖 **Documentation**: [Read the docs](https://docs.manhattan-power-grid.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/manhattan-power-grid/issues)

## 🗺️ Roadmap

### Current Version (v2.0)
- ✅ Complete power grid simulation
- ✅ SUMO vehicle integration
- ✅ V2G energy trading
- ✅ AI analytics and chatbot
- ✅ Professional web interface

### Upcoming Features (v2.1)
- 🔄 Real-time weather integration
- 🔄 Advanced ML demand forecasting
- 🔄 Multi-city support
- 🔄 Mobile app companion

### Future Vision (v3.0)
- 🚀 Distributed grid simulation
- 🚀 Blockchain energy trading
- 🚀 IoT device integration
- 🚀 Digital twin capabilities

---

<div align="center">

**Built with ❤️ for sustainable energy and smart city infrastructure**

[⭐ Star this repo](https://github.com/yourusername/manhattan-power-grid) • [🍴 Fork it](https://github.com/yourusername/manhattan-power-grid/fork) • [📝 Report Issues](https://github.com/yourusername/manhattan-power-grid/issues)

</div>