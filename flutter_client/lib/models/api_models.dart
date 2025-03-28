import 'package:json_annotation/json_annotation.dart';

part 'api_models.g.dart';

/// ZealX API request model
@JsonSerializable()
class ZealXRequest {
  final String userId;
  final String action;
  final dynamic data;
  final String requestId;

  ZealXRequest({
    required this.userId,
    required this.action,
    required this.data,
    required this.requestId,
  });

  factory ZealXRequest.fromJson(Map<String, dynamic> json) =>
      _$ZealXRequestFromJson(json);

  Map<String, dynamic> toJson() => _$ZealXRequestToJson(this);
}

/// ZealX API response model
@JsonSerializable()
class ZealXResponse {
  final bool success;
  final dynamic response;
  final Map<String, dynamic> meta;
  final String requestId;
  final ErrorDetail? error;

  ZealXResponse({
    required this.success,
    required this.response,
    required this.meta,
    required this.requestId,
    this.error,
  });

  factory ZealXResponse.fromJson(Map<String, dynamic> json) =>
      _$ZealXResponseFromJson(json);

  Map<String, dynamic> toJson() => _$ZealXResponseToJson(this);
}

/// Error detail model
@JsonSerializable()
class ErrorDetail {
  final String code;
  final String message;
  final Map<String, dynamic>? details;
  final String? suggestion;

  ErrorDetail({
    required this.code,
    required this.message,
    this.details,
    this.suggestion,
  });

  factory ErrorDetail.fromJson(Map<String, dynamic> json) =>
      _$ErrorDetailFromJson(json);

  Map<String, dynamic> toJson() => _$ErrorDetailToJson(this);
}

/// BrainX request model
@JsonSerializable()
class BrainXRequest {
  final List<Message> messages;
  final double temperature;
  final int max_tokens;
  final bool stream;
  final FireLayersConfig? fire_layers;

  BrainXRequest({
    required this.messages,
    this.temperature = 0.7,
    this.max_tokens = 1024,
    this.stream = false,
    this.fire_layers,
  });

  factory BrainXRequest.fromJson(Map<String, dynamic> json) =>
      _$BrainXRequestFromJson(json);

  Map<String, dynamic> toJson() => _$BrainXRequestToJson(this);
}

/// BrainX response model
@JsonSerializable()
class BrainXResponse {
  final String content;
  final String model;
  final String processing_time;
  final Map<String, dynamic> usage;
  final Map<String, dynamic> fire_layers_stats;

  BrainXResponse({
    required this.content,
    required this.model,
    required this.processing_time,
    required this.usage,
    required this.fire_layers_stats,
  });

  factory BrainXResponse.fromJson(Map<String, dynamic> json) =>
      _$BrainXResponseFromJson(json);

  Map<String, dynamic> toJson() => _$BrainXResponseToJson(this);
}

/// Message model for BrainX
@JsonSerializable()
class Message {
  final String role;
  final String content;

  Message({
    required this.role,
    required this.content,
  });

  factory Message.fromJson(Map<String, dynamic> json) =>
      _$MessageFromJson(json);

  Map<String, dynamic> toJson() => _$MessageToJson(this);
}

/// FireLayers configuration model
@JsonSerializable()
class FireLayersConfig {
  final bool enable_compression;
  final bool enable_adaptive_temp;
  final bool enable_pattern_recognition;
  final double compression_level;
  final double max_temperature;
  final double min_temperature;

  FireLayersConfig({
    this.enable_compression = true,
    this.enable_adaptive_temp = true,
    this.enable_pattern_recognition = true,
    this.compression_level = 0.5,
    this.max_temperature = 1.0,
    this.min_temperature = 0.1,
  });

  factory FireLayersConfig.fromJson(Map<String, dynamic> json) =>
      _$FireLayersConfigFromJson(json);

  Map<String, dynamic> toJson() => _$FireLayersConfigToJson(this);
}

/// AutoX request model
@JsonSerializable()
class AutoXRequest {
  final String app_id;
  final String trigger_type;
  final Map<String, dynamic> trigger_data;
  final int priority;
  final String execution_mode;

  AutoXRequest({
    required this.app_id,
    required this.trigger_type,
    required this.trigger_data,
    this.priority = 1,
    this.execution_mode = 'async',
  });

  factory AutoXRequest.fromJson(Map<String, dynamic> json) =>
      _$AutoXRequestFromJson(json);

  Map<String, dynamic> toJson() => _$AutoXRequestToJson(this);
}

/// AutoX response model
@JsonSerializable()
class AutoXResponse {
  final String task_id;
  final String status;
  final Map<String, dynamic>? result;
  final String? execution_time;

  AutoXResponse({
    required this.task_id,
    required this.status,
    this.result,
    this.execution_time,
  });

  factory AutoXResponse.fromJson(Map<String, dynamic> json) =>
      _$AutoXResponseFromJson(json);

  Map<String, dynamic> toJson() => _$AutoXResponseToJson(this);
}

/// AutoX task model
@JsonSerializable()
class AutoXTask {
  final String task_id;
  final String app_id;
  final String action_type;
  final Map<String, dynamic> action_data;
  final int priority;
  final DateTime created_at;
  final String status;
  final List<AutoXLog> execution_log;

  AutoXTask({
    required this.task_id,
    required this.app_id,
    required this.action_type,
    required this.action_data,
    required this.priority,
    required this.created_at,
    required this.status,
    required this.execution_log,
  });

  factory AutoXTask.fromJson(Map<String, dynamic> json) =>
      _$AutoXTaskFromJson(json);

  Map<String, dynamic> toJson() => _$AutoXTaskToJson(this);
}

/// AutoX log model
@JsonSerializable()
class AutoXLog {
  final String log_id;
  final String task_id;
  final DateTime timestamp;
  final String action;
  final String status;
  final Map<String, dynamic>? details;

  AutoXLog({
    required this.log_id,
    required this.task_id,
    required this.timestamp,
    required this.action,
    required this.status,
    this.details,
  });

  factory AutoXLog.fromJson(Map<String, dynamic> json) =>
      _$AutoXLogFromJson(json);

  Map<String, dynamic> toJson() => _$AutoXLogToJson(this);
}

/// System status model
@JsonSerializable()
class SystemStatus {
  final String status;
  final int uptime;
  final int active_users;
  final double memory_usage;
  final double cpu_usage;
  final ADXStatus adx_status;
  final Map<String, dynamic> api_status;

  SystemStatus({
    required this.status,
    required this.uptime,
    required this.active_users,
    required this.memory_usage,
    required this.cpu_usage,
    required this.adx_status,
    required this.api_status,
  });

  factory SystemStatus.fromJson(Map<String, dynamic> json) =>
      _$SystemStatusFromJson(json);

  Map<String, dynamic> toJson() => _$SystemStatusToJson(this);
}

/// ADX status model
@JsonSerializable()
class ADXStatus {
  final bool is_sleeping;
  final bool power_saving_mode;
  final bool throttling_mode;
  final int monitoring_interval;
  final DateTime last_activity;
  final Map<String, dynamic> stats;

  ADXStatus({
    required this.is_sleeping,
    required this.power_saving_mode,
    required this.throttling_mode,
    required this.monitoring_interval,
    required this.last_activity,
    required this.stats,
  });

  factory ADXStatus.fromJson(Map<String, dynamic> json) =>
      _$ADXStatusFromJson(json);

  Map<String, dynamic> toJson() => _$ADXStatusToJson(this);
}

/// API account status model
@JsonSerializable()
class APIAccountStatus {
  final int total_accounts;
  final int healthy_accounts;
  final int rate_limited_accounts;
  final int error_accounts;
  final List<APIAccount> accounts;

  APIAccountStatus({
    required this.total_accounts,
    required this.healthy_accounts,
    required this.rate_limited_accounts,
    required this.error_accounts,
    required this.accounts,
  });

  factory APIAccountStatus.fromJson(Map<String, dynamic> json) =>
      _$APIAccountStatusFromJson(json);

  Map<String, dynamic> toJson() => _$APIAccountStatusToJson(this);
}

/// API account model
@JsonSerializable()
class APIAccount {
  final String account_id;
  final String status;
  final DateTime last_checked;
  final int consecutive_failures;
  final String? error_message;

  APIAccount({
    required this.account_id,
    required this.status,
    required this.last_checked,
    required this.consecutive_failures,
    this.error_message,
  });

  factory APIAccount.fromJson(Map<String, dynamic> json) =>
      _$APIAccountFromJson(json);

  Map<String, dynamic> toJson() => _$APIAccountToJson(this);
}
