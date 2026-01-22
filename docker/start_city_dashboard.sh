#!/bin/bash
# Start http-server directly from public directory
# Serve login.html as the default page instead of index.html
cd /app/city_dashboard/public
http-server . -p 5000 --cors -a 0.0.0.0 -c-1 --default-index login.html
