curl -X POST "https://authz.constantcontact.com/oauth2/default/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "grant_type=authorization_code" \
  --data "client_id=14140efd-c5c5-4240-996f-e58fc1089ee0" \
  --data "code=bEXnWyXKr459qSJIMymbAqhFdPvEPGEQNV4RkG0RG9E" \
  --data "redirect_uri=http://localhost:3000/oauth/callback" \
  --data "code_verifier=j7VomEbGszwuqAiULNx2SeCPCptog1_a_nBymmVRb5KhSZdkX9iHjhp7SMe6_DbQFaPXlF5xQlvn7wSW5c-CCQ"
