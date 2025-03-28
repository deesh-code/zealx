import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/api_models.dart';
import '../utils/logger.dart';

/// ZealX API Client
/// Handles all communication with the ZealX backend API
class ZealXApiClient {
  // Singleton instance
  static final ZealXApiClient _instance = ZealXApiClient._internal();
  factory ZealXApiClient() => _instance;

  // API configuration
  String baseUrl = 'http://localhost:8000';
  String apiKey = '';
  String userId = '';
  
  // API health tracking
  bool _isConnected = false;
  DateTime? _lastSuccessfulRequest;
  int _consecutiveFailures = 0;
  
  // Request timeout
  Duration timeout = const Duration(seconds: 10);
  
  // HTTP client
  final http.Client _httpClient = http.Client();
  
  // Controller for connection status updates
  final StreamController<bool> _connectionStatusController = 
      StreamController<bool>.broadcast();
  
  // Stream for connection status updates
  Stream<bool> get connectionStatus => _connectionStatusController.stream;
  
  // Getters for connection status
  bool get isConnected => _isConnected;
  DateTime? get lastSuccessfulRequest => _lastSuccessfulRequest;
  
  ZealXApiClient._internal();
  
  /// Initialize the API client with configuration
  Future<void> initialize({
    required String baseUrl,
    required String apiKey,
    required String userId,
  }) async {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.userId = userId;
    
    // Load cached values from shared preferences
    await _loadCachedValues();
    
    // Start connection monitoring
    _startConnectionMonitoring();
    
    AppLogger.info('ZealXApiClient initialized with baseUrl: $baseUrl');
  }
  
  /// Load cached values from shared preferences
  Future<void> _loadCachedValues() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Load cached API key if not provided
      if (apiKey.isEmpty) {
        apiKey = prefs.getString('zealx_api_key') ?? '';
      } else {
        // Save provided API key
        await prefs.setString('zealx_api_key', apiKey);
      }
      
      // Load cached user ID if not provided
      if (userId.isEmpty) {
        userId = prefs.getString('zealx_user_id') ?? '';
      } else {
        // Save provided user ID
        await prefs.setString('zealx_user_id', userId);
      }
      
      // Load cached base URL if not provided
      if (baseUrl.isEmpty) {
        baseUrl = prefs.getString('zealx_base_url') ?? 'http://localhost:8000';
      } else {
        // Save provided base URL
        await prefs.setString('zealx_base_url', baseUrl);
      }
    } catch (e) {
      AppLogger.error('Error loading cached values: $e');
    }
  }
  
  /// Start monitoring connection status
  void _startConnectionMonitoring() {
    // Check connection status periodically
    Timer.periodic(const Duration(seconds: 30), (timer) async {
      await checkConnection();
    });
    
    // Initial connection check
    checkConnection();
  }
  
  /// Check connection to the API
  Future<bool> checkConnection() async {
    try {
      final response = await _httpClient
          .get(Uri.parse('$baseUrl/health'))
          .timeout(timeout);
      
      _isConnected = response.statusCode == 200;
      
      if (_isConnected) {
        _lastSuccessfulRequest = DateTime.now();
        _consecutiveFailures = 0;
      } else {
        _consecutiveFailures++;
      }
      
      // Notify listeners of connection status
      _connectionStatusController.add(_isConnected);
      
      return _isConnected;
    } catch (e) {
      _isConnected = false;
      _consecutiveFailures++;
      
      // Notify listeners of connection status
      _connectionStatusController.add(false);
      
      AppLogger.warning('API connection check failed: $e');
      return false;
    }
  }
  
  /// Get headers for API requests
  Map<String, String> _getHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,
      'User-Agent': 'ZealX-Flutter-Client/1.0',
    };
  }
  
  /// Make a request to the ZealX API
  Future<ZealXResponse> makeRequest({
    required String action,
    required dynamic data,
    String? requestId,
  }) async {
    try {
      // Check connection if we've had consecutive failures
      if (_consecutiveFailures > 0) {
        await checkConnection();
        
        if (!_isConnected) {
          throw Exception('Not connected to the API');
        }
      }
      
      // Create request body
      final request = ZealXRequest(
        userId: userId,
        action: action,
        data: data,
        requestId: requestId ?? _generateRequestId(),
      );
      
      // Make API call
      final response = await _httpClient
          .post(
            Uri.parse('$baseUrl/api/zealx'),
            headers: _getHeaders(),
            body: jsonEncode(request.toJson()),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final responseJson = jsonDecode(response.body);
      return ZealXResponse.fromJson(responseJson);
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('API request failed: $e');
      
      // Return error response
      return ZealXResponse(
        success: false,
        response: null,
        meta: {'error': e.toString()},
        requestId: requestId ?? _generateRequestId(),
        error: ErrorDetail(
          code: 'CONNECTION_ERROR',
          message: 'Failed to connect to the API',
          details: {'error': e.toString()},
          suggestion: 'Check your internet connection and try again',
        ),
      );
    }
  }
  
  /// Send a BrainX request
  Future<BrainXResponse> sendBrainXRequest(BrainXRequest request) async {
    try {
      final response = await _httpClient
          .post(
            Uri.parse('$baseUrl/api/brainx'),
            headers: _getHeaders(),
            body: jsonEncode(request.toJson()),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final responseJson = jsonDecode(response.body);
      return BrainXResponse.fromJson(responseJson);
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('BrainX request failed: $e');
      
      // Return error response
      return BrainXResponse(
        content: 'Error: Failed to connect to BrainX',
        model: 'unknown',
        processing_time: '0ms',
        usage: {'error': true},
        fire_layers_stats: {'error': true},
      );
    }
  }
  
  /// Send an AutoX request
  Future<AutoXResponse> sendAutoXRequest(AutoXRequest request) async {
    try {
      final response = await _httpClient
          .post(
            Uri.parse('$baseUrl/api/autox'),
            headers: _getHeaders(),
            body: jsonEncode(request.toJson()),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final responseJson = jsonDecode(response.body);
      return AutoXResponse.fromJson(responseJson);
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('AutoX request failed: $e');
      
      // Return error response
      return AutoXResponse(
        task_id: 'error',
        status: 'failed',
        result: {'error': e.toString()},
        execution_time: '0ms',
      );
    }
  }
  
  /// Get system status
  Future<SystemStatus> getSystemStatus() async {
    try {
      final response = await _httpClient
          .get(
            Uri.parse('$baseUrl/api/system/status'),
            headers: _getHeaders(),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final responseJson = jsonDecode(response.body);
      return SystemStatus.fromJson(responseJson);
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('System status request failed: $e');
      
      // Return error response
      return SystemStatus(
        status: 'offline',
        uptime: 0,
        active_users: 0,
        memory_usage: 0,
        cpu_usage: 0,
        adx_status: ADXStatus(
          is_sleeping: false,
          power_saving_mode: false,
          throttling_mode: false,
          monitoring_interval: 0,
          last_activity: DateTime.now(),
          stats: {},
        ),
        api_status: {},
      );
    }
  }
  
  /// Get API account status
  Future<APIAccountStatus> getAPIAccountStatus() async {
    try {
      final response = await _httpClient
          .get(
            Uri.parse('$baseUrl/api/system/api_status'),
            headers: _getHeaders(),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final responseJson = jsonDecode(response.body);
      return APIAccountStatus.fromJson(responseJson);
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('API account status request failed: $e');
      
      // Return error response
      return APIAccountStatus(
        total_accounts: 0,
        healthy_accounts: 0,
        rate_limited_accounts: 0,
        error_accounts: 0,
        accounts: [],
      );
    }
  }
  
  /// Get AutoX task details
  Future<AutoXTask> getAutoXTask(String taskId) async {
    try {
      final response = await _httpClient
          .get(
            Uri.parse('$baseUrl/api/autox/tasks/$taskId'),
            headers: _getHeaders(),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final responseJson = jsonDecode(response.body);
      return AutoXTask.fromJson(responseJson);
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('Get AutoX task request failed: $e');
      
      // Return error response
      return AutoXTask(
        task_id: taskId,
        app_id: 'unknown',
        action_type: 'unknown',
        action_data: {},
        priority: 0,
        created_at: DateTime.now(),
        status: 'error',
        execution_log: [],
      );
    }
  }
  
  /// Get recent AutoX tasks
  Future<List<AutoXTask>> getRecentAutoXTasks({int limit = 10}) async {
    try {
      final response = await _httpClient
          .get(
            Uri.parse('$baseUrl/api/autox/tasks?limit=$limit'),
            headers: _getHeaders(),
          )
          .timeout(timeout);
      
      // Update connection status
      _isConnected = true;
      _lastSuccessfulRequest = DateTime.now();
      _consecutiveFailures = 0;
      
      // Parse response
      final List<dynamic> responseJson = jsonDecode(response.body);
      return responseJson.map((json) => AutoXTask.fromJson(json)).toList();
    } catch (e) {
      _consecutiveFailures++;
      
      if (_consecutiveFailures > 3) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      
      AppLogger.error('Get recent AutoX tasks request failed: $e');
      
      // Return empty list
      return [];
    }
  }
  
  /// Generate a unique request ID
  String _generateRequestId() {
    return 'req_${DateTime.now().millisecondsSinceEpoch}_${userId.hashCode}';
  }
  
  /// Dispose the API client
  void dispose() {
    _httpClient.close();
    _connectionStatusController.close();
  }
}
