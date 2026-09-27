#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "$0")/common.sh"
require_env
read -r -p 'Admin username: ' username
read -r -p 'Admin full name: ' fullname
read -r -s -p 'Initial password (12+ chars): ' password
echo
[[ ${#password} -ge 12 ]] || { echo 'Password must be at least 12 characters.' >&2; exit 2; }
printf '%s\n%s\n%s\n' "$username" "$fullname" "$password" | dc exec -T dashboard python -c 'import sys,os,psycopg2; from auth import hash_password; u,n,p=[x.rstrip("\n") for x in sys.stdin]; c=psycopg2.connect(host=os.environ["POSTGRES_HOST"],dbname=os.environ["CS_DB_NAME"],user=os.environ["CS_DB_USER"],password=os.environ["CS_DB_PASSWORD"]); q=c.cursor(); q.execute("INSERT INTO admin_users(username,password_hash,full_name,role,must_change_password) VALUES (%s,%s,%s,%s,TRUE) ON CONFLICT(username) DO NOTHING",(u,hash_password(p),n,"admin")); c.commit(); q.close(); c.close(); print("Admin account created if username was new.")'
unset password
