#!/bin/bash
# Start http-server from city_dashboard directory
# Serve root but redirect / to /public/index.html
cd /app/city_dashboard
http-server . -p 5000 --cors -a 0.0.0.0 --proxy http://localhost:5000/public/index.html?
