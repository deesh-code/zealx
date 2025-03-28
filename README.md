# ZealX Backend

A powerful AI-powered digital twin and automation system with adaptive learning capabilities.

## Overview

ZealX is a comprehensive backend system that combines several powerful components:

- **BrainX**: AI-powered digital twin with adaptive learning capabilities
- **AutoX**: Automation system with task scheduling and execution
- **FireLayers X++**: Adaptive learning system for optimizing AI interactions
- **ADX (Adaptive Execution Mode)**: Battery and performance optimization

## Key Features

- **Structured API Responses**: Consistent error handling and response formats
- **Multi-Account API Management**: Fast failover between API accounts
- **Adaptive Learning**: FireLayers X++ system for optimizing AI interactions
- **Battery Optimization**: ADX system to prevent battery drain
- **Comprehensive Logging**: Structured logging for all AutoX actions
- **API Security**: Rate limiting, authentication, and secure headers
- **Flutter Integration**: Complete Flutter client for mobile app integration

## Architecture

The ZealX backend is built with FastAPI and follows a modular architecture:

```
backend/
├── core/
│   ├── config.py             # Configuration settings
│   ├── firelayers.py         # FireLayers X++ adaptive learning
│   └── logging_manager.py    # Structured logging system
├── middleware/
│   ├── api_account_manager.py # Multi-account API management
│   ├── error_handlers.py     # Error handling middleware
│   └── security.py           # Security and rate limiting
├── models/
│   └── api.py                # API data models
├── routers/
│   └── api_router.py         # API endpoints
└── app.py                    # Main application
```

## Getting Started

### Prerequisites

- Python 3.8+
- Redis
- PostgreSQL (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/zealx.git
   cd zealx
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with the following variables:
   ```
   # App settings
   DEBUG=true
   ENVIRONMENT=development
   
   # API keys
   CLOUDFLARE_API_KEYS=your_api_key_1,your_api_key_2
   CLOUDFLARE_ACCOUNT_IDS=your_account_id_1,your_account_id_2
   CLOUDFLARE_WORKER_URLS=https://worker1.yourworker.workers.dev,https://worker2.yourworker.workers.dev
   
   # Redis settings
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=
   REDIS_DB=0
   
   # Security settings
   SECRET_KEY=your_secret_key
   API_KEY=your_api_key
   ```

### Running the Backend

Start the ZealX backend:

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## Flutter Client

The Flutter client provides a complete integration with the ZealX backend:

```
flutter_client/
├── lib/
│   ├── api/
│   │   └── zealx_api_client.dart  # API client for ZealX
│   ├── models/
│   │   └── api_models.dart        # API data models
│   └── utils/
│       └── logger.dart            # Logging utility
```

### Using the Flutter Client

1. Add the required dependencies to your `pubspec.yaml`:
   ```yaml
   dependencies:
     http: ^0.13.5
     shared_preferences: ^2.1.0
     json_annotation: ^4.8.0
     intl: ^0.18.0
     path_provider: ^2.0.14
   
   dev_dependencies:
     build_runner: ^2.3.3
     json_serializable: ^6.6.1
   ```

2. Generate the model code:
   ```bash
   cd flutter_client
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

3. Initialize the API client in your app:
   ```dart
   import 'package:your_app/api/zealx_api_client.dart';
   import 'package:your_app/utils/logger.dart';
   
   Future<void> main() async {
     // Initialize logger
     await AppLogger.initialize(
       logLevel: AppLogger.INFO,
       enableFileLogging: true,
     );
     
     // Initialize API client
     await ZealXApiClient().initialize(
       baseUrl: 'http://your-server:8000',
       apiKey: 'your_api_key',
       userId: 'user_123',
     );
     
     runApp(MyApp());
   }
   ```

## ADX (Adaptive Execution Mode)

The ADX system optimizes battery usage and performance by adapting execution based on device conditions:

- **Auto-Sleep Mode**: Pauses or reduces activity when the device is inactive
- **Smart Resume**: Wakes up only when needed based on event priority
- **Dynamic Adjustment**: Adjusts execution intensity based on device metrics

ADX operates in several states:
- **Normal**: Full functionality, regular checking intervals
- **Optimized**: Slightly reduced activity to balance performance and battery
- **Conservative**: Significantly reduced activity to save battery
- **Suspended**: Minimal activity, only critical tasks are processed

## FireLayers X++

FireLayers X++ is an adaptive learning system that optimizes interactions with AI models:

- **Context Compression**: Reduces token usage while preserving meaning
- **Dynamic Temperature Adjustment**: Adapts model creativity based on context
- **Pattern Recognition**: Identifies and optimizes recurring patterns

## API Security

The ZealX API includes comprehensive security features:

- **Rate Limiting**: Prevents abuse with configurable limits per endpoint
- **API Key Authentication**: Secures API access
- **Security Headers**: Protects against common web vulnerabilities
- **CORS Protection**: Controls cross-origin requests

## License

This project is licensed under the MIT License - see the LICENSE file for details.
