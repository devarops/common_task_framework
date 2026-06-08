curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
  "model": "openrouter/free",
  "messages": [
    {
      "role": "user",
      "content": "Hello World"
    }
  ]
}'

