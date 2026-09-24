@echo off
rem One-step JARVIS launcher. Usage: jarvis [start|stop|restart|status] [--rebuild]
node "%~dp0scripts\launch.mjs" %*
