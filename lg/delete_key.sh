curl -X DELETE "https://xxeucrngdl.execute-api.us-west-2.amazonaws.com/api/v1/api-key/$1" \
  -H "X-API-Key: $LANGSMITH_ADMIN_API_KEY" \
  -H "X-Organization-Id: $ORG_KEY" \
