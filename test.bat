curl.exe localhost:8000/health
curl.exe -c c.txt -X POST localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"email\":\"admin@frill.pk\",\"password\":\"ChangeMeNow123!\"}"
curl.exe -b c.txt localhost:8000/auth/me
curl.exe localhost:8000/api/products
FOR /L %%i IN (1,1,6) DO curl.exe -s -o NUL -w "%%{http_code}\n" -X POST localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"email\":\"x@x.com\",\"password\":\"wrong\"}"
