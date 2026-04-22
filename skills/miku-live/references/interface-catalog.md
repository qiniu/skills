# Miku 接口清单参考

## 执行约束

- 命中与归位：仅用 `action_key` 命中接口行；按接口总表列定义组装 `host/path/query/body`，且先替换 host/path 占位符。
- 校验：参数不得跨位置；`GET/DELETE` 默认无 body（接口行显式要求除外）；query 键名取 `path` 模板字面量并严格区分大小写（如 `certName=<cert_name>`）；跨位置同名参数值必须一致。
- 错误：`PARAM_POSITION_MISMATCH` / `UNDECLARED_PARAM` / `PARAM_VALUE_CONFLICT`；缺参返回位置化 `missing_required`。

## 接口总表

| action_key | method | domain | path | required_params | optional_params | required_query_params | optional_query_params | required_host_params | required_path_params |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `bucket-management/create_bucket` | `PUT` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/` | `-` | `-` | `-` | `-` | `bucket_name` | `-` |
| `bucket-management/delete_bucket` | `DELETE` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/` | `-` | `-` | `-` | `-` | `bucket_name` | `-` |
| `bucket-management/get_bucket_config` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?config` | `-` | `-` | `-` | `with_config` | `bucket_name` | `-` |
| `bucket-management/list_buckets` | `GET` | `mls.cn-east-1.qiniumiku.com` | `/` | `-` | `-` | `-` | `-` | `-` | `-` |
| `bucket-management/update_bucket_config` | `PATCH` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?config` | `config_data` | `-` | `-` | `-` | `bucket_name` | `-` |
| `certificate-management/delete_domain_certificate` | `DELETE` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domainCertificate&domain=<domain>&certName=<cert_name>` | `-` | `-` | `domain`、`cert_name` | `-` | `bucket_name` | `-` |
| `certificate-management/list_domain_certificates` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domainCertificate&domain=<domain>` | `-` | `-` | `domain` | `-` | `bucket_name` | `-` |
| `certificate-management/update_certificate` | `PATCH` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domainCertificate&domain=<domain>&certName=<cert_name>` | `update_data` | `-` | `domain`、`cert_name` | `-` | `bucket_name` | `-` |
| `certificate-management/upload_domain_certificate` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domainCertificate` | `certificate_data` | `-` | `-` | `-` | `bucket_name` | `-` |
| `domain-management/bind_downstream_domain` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domain` | `domain` | `domain_type` | `-` | `-` | `bucket_name` | `-` |
| `domain-management/bind_upstream_domain` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?pushDomain` | `domain`、`domain_type` | `-` | `-` | `-` | `bucket_name` | `-` |
| `domain-management/get_downstream_domain_config` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domainConfig&name=<domain>` | `-` | `-` | `domain` | `-` | `bucket_name` | `-` |
| `domain-management/get_upstream_domain_config` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?pushDomainConfig&name=<domain>` | `-` | `-` | `domain` | `-` | `bucket_name` | `-` |
| `domain-management/list_downstream_domains` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domain` | `-` | `-` | `-` | `-` | `bucket_name` | `-` |
| `domain-management/list_upstream_domains` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?pushDomain` | `-` | `-` | `-` | `-` | `bucket_name` | `-` |
| `domain-management/unbind_downstream_domain` | `DELETE` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domain&name=<domain>` | `-` | `-` | `domain` | `-` | `bucket_name` | `-` |
| `domain-management/unbind_upstream_domain` | `DELETE` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?pushDomain&name=<domain>` | `-` | `-` | `domain` | `-` | `bucket_name` | `-` |
| `domain-management/update_downstream_domain_config` | `PATCH` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?domainConfig&name=<domain>[&fields=<fields>]` | `config_data` | `-` | `domain` | `fields` | `bucket_name` | `-` |
| `domain-management/update_upstream_domain_config` | `PATCH` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/?pushDomainConfig&name=<domain>[&fields=<fields>]` | `config_data` | `-` | `domain` | `fields` | `bucket_name` | `-` |
| `live-stream-transcoding-template/add_transcoding_template` | `POST` | `mls.cn-east-1.qiniumiku.com` | `/?codecTemplate` | `template_body` | `host` | `-` | `-` | `-` | `-` |
| `live-stream-transcoding-template/delete_transcoding_template` | `DELETE` | `mls.cn-east-1.qiniumiku.com` | `/?codecTemplate&name=<name>` | `-` | `host` | `name` | `-` | `-` | `-` |
| `live-stream-transcoding-template/get_template_info` | `GET` | `mls.cn-east-1.qiniumiku.com` | `/?codecTemplate&name=<name>` | `-` | `host` | `name` | `-` | `-` | `-` |
| `live-stream-transcoding-template/get_template_list` | `GET` | `mls.cn-east-1.qiniumiku.com` | `/?codecTemplates[&content=<content>&limit=<limit>&offset=<offset>]` | `-` | `host` | `-` | `content`、`limit`、`offset` | `-` | `-` |
| `live-stream-transcoding-template/update_transcoding_template` | `PATCH` | `mls.cn-east-1.qiniumiku.com` | `/?codecTemplate` | `template_body` | `host` | `-` | `-` | `-` | `-` |
| `pub-relay/create_pub_task` | `POST` | `pub-manager.mikudns.com` | `/tasks` | `task_body` | `-` | `-` | `-` | `-` | `-` |
| `pub-relay/delete_pub_task` | `DELETE` | `pub-manager.mikudns.com` | `/tasks/<task_id>` | `-` | `-` | `-` | `-` | `-` | `task_id` |
| `pub-relay/edit_pub_task` | `POST` | `pub-manager.mikudns.com` | `/tasks/<task_id>` | `task_body` | `-` | `-` | `-` | `-` | `task_id` |
| `pub-relay/get_pub_list` | `GET` | `pub-manager.mikudns.com` | `/tasks[?marker=<marker>&limit=<limit>&name=<name>]` | `-` | `-` | `-` | `marker`、`limit`、`name` | `-` | `-` |
| `pub-relay/query_pub_task` | `GET` | `pub-manager.mikudns.com` | `/tasks/<task_id>` | `-` | `-` | `-` | `-` | `-` | `task_id` |
| `pub-relay/query_task_history` | `GET` | `pub-manager.mikudns.com` | `/history[?marker=<marker>&limit=<limit>&name=<name>&start=<start>&end=<end>]` | `-` | `-` | `-` | `marker`、`limit`、`name`、`start`、`end` | `-` | `-` |
| `pub-relay/query_task_log` | `GET` | `pub-manager.mikudns.com` | `/tasks/<task_id>/runinfo` | `-` | `-` | `-` | `-` | `-` | `task_id` |
| `pub-relay/start_pub_task` | `POST` | `pub-manager.mikudns.com` | `/tasks/<task_id>/start` | `-` | `-` | `-` | `-` | `-` | `task_id` |
| `pub-relay/stop_pub_task` | `POST` | `pub-manager.mikudns.com` | `/tasks/<task_id>/stop` | `-` | `-` | `-` | `-` | `-` | `task_id` |
| `recording-management/create_recording` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_name>?recordingFile` | `start_time`、`end_time` | `fmt`、`fname`、`pipeline`、`expire_days`、`first_segment_type`、`persistent_delete_after_days`、`notify`、`host`、`timeout` | `-` | `-` | `bucket_name` | `stream_name` |
| `recording-management/snapshot` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_name>?snapshot` | `-` | `time`、`fname`、`img_format`、`pipeline`、`notify`、`delete_after_days` | `-` | `-` | `bucket_name` | `stream_name` |
| `statistics/query_downflow_stat` | `GET` | `miku-statd.qiniuapi.com` | `/statd/v1/traffic/stat/downflow` | `-` | `-` | `begin` | `end`、`granularity`、`group`、`hub`、`domain`、`stream_name`、`area`、`select` | `-` | `-` |
| `statistics/query_offline_log` | `GET` | `miku-statd.qiniuapi.com` | `/statd/v1/livelog` | `-` | `-` | `domain`、`start`、`end` | `-` | `-` | `-` |
| `statistics/query_split_offline_log` | `GET` | `miku-statd.qiniuapi.com` | `/statd/v1/livelog/split` | `-` | `-` | `domain`、`start`、`end` | `-` | `-` | `-` |
| `statistics/query_stream_history` | `GET` | `mls.cn-east-1.qiniumiku.com` | `/?streamStats&start=<start>&end=<end>&stream=<stream>[&domain=<domain>][&bucket=<bucket>][&g=<granularity>]` | `-` | `-` | `start`、`end`、`stream` | `domain`、`bucket`、`granularity` | `-` | `-` |
| `statistics/query_upflow_stat` | `GET` | `miku-statd.qiniuapi.com` | `/statd/v1/traffic/stat/upflow` | `-` | `-` | `begin` | `end`、`granularity`、`group`、`hub`、`domain`、`stream_name`、`area`、`select` | `-` | `-` |
| `stream-management/ban_stream` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>?forbid&bucket=<bucket_name>&streamKey=<stream_key>` | `-` | `forbidden_till` | `bucket_name`、`stream_key` | `-` | `bucket_name` | `stream_key` |
| `stream-management/create_stream` | `PUT` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>` | `-` | `-` | `-` | `-` | `bucket_name` | `stream_key` |
| `stream-management/delete_stream` | `DELETE` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>` | `-` | `-` | `-` | `-` | `bucket_name` | `stream_key` |
| `stream-management/get_stream_info` | `GET` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>?info=` | `-` | `-` | `-` | `-` | `bucket_name` | `stream_key` |
| `stream-management/get_stream_list` | `GET` | `mls.cn-east-1.qiniumiku.com` | `/?streamlist[&prefix=<prefix>&offset=<offset>&limit=<limit>&domain=<domain>&start=<start>&end=<end>&bucketId=<bucketId>&isForbid=<isForbid>]` | `-` | `-` | `-` | `domain`、`bucketId`、`prefix`、`offset`、`limit`、`start`、`end`、`isForbid` | `-` | `-` |
| `stream-management/unban_stream` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>?release` | `-` | `-` | `-` | `-` | `bucket_name` | `stream_key` |
| `utilities/create_apikey` | `POST` | `mls.cn-east-1.qiniumiku.com` | `/?apikey` | `name` | `-` | `-` | `-` | `-` | `-` |
| `utilities/delete_apikey` | `DELETE` | `mls.cn-east-1.qiniumiku.com` | `/?apikey` | `apikey_id` | `-` | `-` | `-` | `-` | `-` |
| `utilities/query_apikey_list` | `GET` | `mls.cn-east-1.qiniumiku.com` | `/?apikeys` | `-` | `-` | `-` | `-` | `-` | `-` |
| `utilities/rename_apikey` | `POST` | `mls.cn-east-1.qiniumiku.com` | `/?apikeyRename` | `apikey_id`、`new_name` | `-` | `-` | `-` | `-` | `-` |
| `utilities/query_play_domain` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>?playUrl` | `domain` | `expire_time` | `-` | `-` | `bucket_name` | `stream_key` |
| `utilities/query_publish_domain` | `POST` | `<bucket_name>.mls.cn-east-1.qiniumiku.com` | `/<stream_key>?publishUrl` | `domain` | `expire_time` | `-` | `-` | `bucket_name` | `stream_key` |

## 接口级联动约束

- `statistics/query_stream_history`：`domain` 与 `bucket` 至少提供一个。
- `stream-management/get_stream_list`：`domain` 与 `bucketId` 至少提供一个。
