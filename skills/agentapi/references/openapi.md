<!-- 由 scripts/sync-docs.py 自动生成。 -->

# OpenAPI 规范

原文：<https://developer.qiniu.com/agentapi/13619/agentapi-openapi>

完整请求、响应字段和数据结构见 [下载 OpenAPI YAML](openapi.yaml)。该文件可导入支持 OpenAPI 的接口工具。

## 接口索引

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | \`/v1/agents\` | List agents |
| POST | \`/v1/agents\` | Create agent |
| DELETE | \`/v1/agents/{id}\` | Delete agent |
| GET | \`/v1/agents/{id}\` | Get agent |
| PATCH | \`/v1/agents/{id}\` | Patch agent |
| POST | \`/v1/agents/{id}\` | Update agent |
| POST | \`/v1/agents/{id}/archive\` | Archive agent |
| GET | \`/v1/agents/{id}/versions\` | List agent versions |
| GET | \`/v1/deployment\_runs\` | List deployment runs |
| GET | \`/v1/deployment\_runs/{deployment\_run\_id}\` | Get deployment run |
| GET | \`/v1/deployments\` | List deployments |
| POST | \`/v1/deployments\` | Create deployment |
| GET | \`/v1/deployments/{deployment\_id}\` | Get deployment |
| POST | \`/v1/deployments/{deployment\_id}\` | Update deployment |
| POST | \`/v1/deployments/{deployment\_id}/archive\` | Archive deployment |
| POST | \`/v1/deployments/{deployment\_id}/pause\` | Pause deployment |
| POST | \`/v1/deployments/{deployment\_id}/run\` | Run deployment now |
| POST | \`/v1/deployments/{deployment\_id}/unpause\` | Unpause deployment |
| GET | \`/v1/environments\` | List environments |
| POST | \`/v1/environments\` | Create environment |
| GET | \`/v1/environments/{environment\_id}/work\` | List self-hosted work |
| GET | \`/v1/environments/{environment\_id}/work/poll\` | Poll self-hosted environment work |
| GET | \`/v1/environments/{environment\_id}/work/stats\` | Get self-hosted work queue stats |
| GET | \`/v1/environments/{environment\_id}/work/{work\_id}\` | Get self-hosted work |
| POST | \`/v1/environments/{environment\_id}/work/{work\_id}\` | Update self-hosted work metadata |
| POST | \`/v1/environments/{environment\_id}/work/{work\_id}/ack\` | Acknowledge self-hosted work |
| POST | \`/v1/environments/{environment\_id}/work/{work\_id}/heartbeat\` | Heartbeat self-hosted work |
| POST | \`/v1/environments/{environment\_id}/work/{work\_id}/stop\` | Stop self-hosted work |
| DELETE | \`/v1/environments/{id}\` | Delete environment |
| GET | \`/v1/environments/{id}\` | Get environment |
| POST | \`/v1/environments/{id}\` | Update environment |
| POST | \`/v1/environments/{id}/archive\` | Archive environment |
| GET | \`/v1/files\` | List files |
| POST | \`/v1/files\` | Upload file |
| DELETE | \`/v1/files/{id}\` | Delete file |
| GET | \`/v1/files/{id}\` | Get file metadata |
| GET | \`/v1/files/{id}/content\` | Download file content |
| GET | \`/v1/memory\_stores\` | List memory stores |
| POST | \`/v1/memory\_stores\` | Create memory store |
| DELETE | \`/v1/memory\_stores/{memory\_store\_id}\` | Delete memory store |
| GET | \`/v1/memory\_stores/{memory\_store\_id}\` | Get memory store |
| POST | \`/v1/memory\_stores/{memory\_store\_id}\` | Update memory store |
| POST | \`/v1/memory\_stores/{memory\_store\_id}/archive\` | Archive memory store |
| GET | \`/v1/memory\_stores/{memory\_store\_id}/memories\` | List memories |
| POST | \`/v1/memory\_stores/{memory\_store\_id}/memories\` | Create memory |
| DELETE | \`/v1/memory\_stores/{memory\_store\_id}/memories/{memory\_id}\` | Delete memory |
| GET | \`/v1/memory\_stores/{memory\_store\_id}/memories/{memory\_id}\` | Get memory |
| POST | \`/v1/memory\_stores/{memory\_store\_id}/memories/{memory\_id}\` | Update memory |
| GET | \`/v1/memory\_stores/{memory\_store\_id}/memory\_versions\` | List memory versions |
| GET | \`/v1/memory\_stores/{memory\_store\_id}/memory\_versions/{memory\_version\_id}\` | Get memory version |
| POST | \`/v1/memory\_stores/{memory\_store\_id}/memory\_versions/{memory\_version\_id}/redact\` | Redact memory version |
| GET | \`/v1/sessions\` | List sessions |
| POST | \`/v1/sessions\` | Create session |
| DELETE | \`/v1/sessions/{id}\` | Delete session |
| GET | \`/v1/sessions/{id}\` | Get session |
| POST | \`/v1/sessions/{id}\` | Update session |
| POST | \`/v1/sessions/{id}/archive\` | Archive session |
| GET | \`/v1/sessions/{id}/events\` | List session events |
| POST | \`/v1/sessions/{id}/events\` | Send session events |
| GET | \`/v1/sessions/{id}/events/stream\` | Stream session events |
| GET | \`/v1/sessions/{id}/resources\` | List session resources |
| POST | \`/v1/sessions/{id}/resources\` | Add session resource |
| DELETE | \`/v1/sessions/{id}/resources/{resource\_id}\` | Delete session resource |
| GET | \`/v1/sessions/{id}/resources/{resource\_id}\` | Get session resource |
| POST | \`/v1/sessions/{id}/resources/{resource\_id}\` | Update session resource |
| GET | \`/v1/skills\` | List skills |
| POST | \`/v1/skills\` | Create skill |
| DELETE | \`/v1/skills/{skill\_id}\` | Delete skill |
| GET | \`/v1/skills/{skill\_id}\` | Get skill |
| GET | \`/v1/skills/{skill\_id}/versions\` | List skill versions |
| POST | \`/v1/skills/{skill\_id}/versions\` | Create skill version |
| DELETE | \`/v1/skills/{skill\_id}/versions/{version}\` | Delete skill version |
| GET | \`/v1/skills/{skill\_id}/versions/{version}\` | Get skill version |
| GET | \`/v1/skills/{skill\_id}/versions/{version}/content\` | Download skill version content |
| GET | \`/v1/skills/{skill\_id}/versions/{version}/files\` | List skill version files |
| GET | \`/v1/skills/{skill\_id}/versions/{version}/files/content\` | Download skill version file content |
| GET | \`/v1/vaults\` | List vaults |
| POST | \`/v1/vaults\` | Create vault |
| DELETE | \`/v1/vaults/{vault\_id}\` | Delete vault |
| GET | \`/v1/vaults/{vault\_id}\` | Get vault |
| POST | \`/v1/vaults/{vault\_id}\` | Update vault |
| POST | \`/v1/vaults/{vault\_id}/archive\` | Archive vault |
| GET | \`/v1/vaults/{vault\_id}/credentials\` | List credentials |
| POST | \`/v1/vaults/{vault\_id}/credentials\` | Create credential |
| DELETE | \`/v1/vaults/{vault\_id}/credentials/{credential\_id}\` | Delete credential |
| GET | \`/v1/vaults/{vault\_id}/credentials/{credential\_id}\` | Get credential |
| POST | \`/v1/vaults/{vault\_id}/credentials/{credential\_id}\` | Update credential |
| POST | \`/v1/vaults/{vault\_id}/credentials/{credential\_id}/archive\` | Archive credential |
