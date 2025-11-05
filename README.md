compile: python start_sampleapp.py --server-port 8000
python start_sampleapp.py --server-port 9001
python start_sampleapp.py --server-port 9002
web: http://localhost:9001/index.html ---> 401 Unauthor if not signin yet
http://localhost:9001/login.html --> "admin", "password"
do the same with 9002
