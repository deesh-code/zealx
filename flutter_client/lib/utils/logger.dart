import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

/// AppLogger
/// Provides logging functionality for the ZealX Flutter client
/// Supports console logging and file logging with different log levels
class AppLogger {
  // Log levels
  static const int VERBOSE = 0;
  static const int DEBUG = 1;
  static const int INFO = 2;
  static const int WARNING = 3;
  static const int ERROR = 4;
  static const int NONE = 5;

  // Current log level
  static int _currentLogLevel = kDebugMode ? DEBUG : INFO;
  
  // Log file
  static File? _logFile;
  static bool _fileLoggingEnabled = false;
  static const int _maxLogFileSize = 5 * 1024 * 1024; // 5 MB
  
  // Date formatter for log entries
  static final DateFormat _dateFormatter = DateFormat('yyyy-MM-dd HH:mm:ss.SSS');
  
  /// Initialize the logger
  static Future<void> initialize({
    int logLevel = INFO,
    bool enableFileLogging = true,
  }) async {
    _currentLogLevel = logLevel;
    _fileLoggingEnabled = enableFileLogging;
    
    if (_fileLoggingEnabled) {
      await _initializeLogFile();
    }
    
    info('AppLogger initialized with log level: ${_getLevelName(logLevel)}');
  }
  
  /// Initialize the log file
  static Future<void> _initializeLogFile() async {
    try {
      final Directory appDocDir = await getApplicationDocumentsDirectory();
      final String logDirPath = '${appDocDir.path}/logs';
      
      // Create logs directory if it doesn't exist
      final Directory logDir = Directory(logDirPath);
      if (!await logDir.exists()) {
        await logDir.create(recursive: true);
      }
      
      // Create log file
      final String timestamp = DateFormat('yyyyMMdd').format(DateTime.now());
      final String logFilePath = '$logDirPath/zealx_$timestamp.log';
      _logFile = File(logFilePath);
      
      // Create file if it doesn't exist
      if (!await _logFile!.exists()) {
        await _logFile!.create();
      }
      
      // Check file size and rotate if needed
      await _checkLogFileSize();
      
      debug('Log file initialized: $logFilePath');
    } catch (e) {
      _fileLoggingEnabled = false;
      error('Failed to initialize log file: $e');
    }
  }
  
  /// Check log file size and rotate if needed
  static Future<void> _checkLogFileSize() async {
    if (_logFile != null && await _logFile!.exists()) {
      final int fileSize = await _logFile!.length();
      
      if (fileSize > _maxLogFileSize) {
        // Rotate log file
        final String oldPath = _logFile!.path;
        final String timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
        final String newPath = '${oldPath.substring(0, oldPath.lastIndexOf('.'))}_$timestamp.log';
        
        await _logFile!.rename(newPath);
        
        // Create new log file
        _logFile = File(oldPath);
        await _logFile!.create();
        
        debug('Log file rotated: $newPath');
      }
    }
  }
  
  /// Log a verbose message
  static void verbose(String message) {
    _log(VERBOSE, message);
  }
  
  /// Log a debug message
  static void debug(String message) {
    _log(DEBUG, message);
  }
  
  /// Log an info message
  static void info(String message) {
    _log(INFO, message);
  }
  
  /// Log a warning message
  static void warning(String message) {
    _log(WARNING, message);
  }
  
  /// Log an error message
  static void error(String message, [dynamic error, StackTrace? stackTrace]) {
    String logMessage = message;
    
    if (error != null) {
      logMessage += '\nError: $error';
    }
    
    if (stackTrace != null) {
      logMessage += '\nStackTrace: $stackTrace';
    }
    
    _log(ERROR, logMessage);
  }
  
  /// Log a message with the specified level
  static void _log(int level, String message) {
    if (level < _currentLogLevel) {
      return;
    }
    
    final String timestamp = _dateFormatter.format(DateTime.now());
    final String levelName = _getLevelName(level);
    final String logEntry = '[$timestamp] $levelName: $message';
    
    // Log to console
    if (kDebugMode) {
      developer.log(
        message,
        name: 'ZealX',
        level: level,
        time: DateTime.now(),
      );
    }
    
    // Log to file
    _writeToLogFile(logEntry);
  }
  
  /// Write a log entry to the log file
  static Future<void> _writeToLogFile(String logEntry) async {
    if (!_fileLoggingEnabled || _logFile == null) {
      return;
    }
    
    try {
      await _checkLogFileSize();
      await _logFile!.writeAsString('$logEntry\n', mode: FileMode.append);
    } catch (e) {
      // Don't log this error to avoid infinite recursion
      if (kDebugMode) {
        print('Failed to write to log file: $e');
      }
    }
  }
  
  /// Get the name of a log level
  static String _getLevelName(int level) {
    switch (level) {
      case VERBOSE:
        return 'VERBOSE';
      case DEBUG:
        return 'DEBUG';
      case INFO:
        return 'INFO';
      case WARNING:
        return 'WARNING';
      case ERROR:
        return 'ERROR';
      default:
        return 'UNKNOWN';
    }
  }
  
  /// Set the current log level
  static void setLogLevel(int level) {
    _currentLogLevel = level;
    info('Log level changed to: ${_getLevelName(level)}');
  }
  
  /// Enable or disable file logging
  static Future<void> setFileLogging(bool enabled) async {
    if (enabled && !_fileLoggingEnabled) {
      _fileLoggingEnabled = true;
      await _initializeLogFile();
      info('File logging enabled');
    } else if (!enabled && _fileLoggingEnabled) {
      _fileLoggingEnabled = false;
      info('File logging disabled');
    }
  }
  
  /// Get all log files
  static Future<List<File>> getLogFiles() async {
    try {
      final Directory appDocDir = await getApplicationDocumentsDirectory();
      final String logDirPath = '${appDocDir.path}/logs';
      
      final Directory logDir = Directory(logDirPath);
      if (!await logDir.exists()) {
        return [];
      }
      
      final List<FileSystemEntity> entities = await logDir.list().toList();
      return entities
          .whereType<File>()
          .where((file) => file.path.endsWith('.log'))
          .toList();
    } catch (e) {
      error('Failed to get log files: $e');
      return [];
    }
  }
  
  /// Clear all log files
  static Future<void> clearLogFiles() async {
    try {
      final List<File> logFiles = await getLogFiles();
      
      for (final File file in logFiles) {
        await file.delete();
      }
      
      info('All log files cleared');
    } catch (e) {
      error('Failed to clear log files: $e');
    }
  }
}
