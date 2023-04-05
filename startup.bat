@echo off

REM Update the local main branch to the latest version
git checkout main
git pull

REM Start up Chatbot
python chat.py