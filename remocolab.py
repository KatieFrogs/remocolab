import pathlib, stat, shutil, urllib.request, subprocess, time
import json, sys
import os, psutil

def _log(message):
	print("[%s] %s" % (time.strftime("%H:%M:%S", time.localtime()), message))

def _download(url, path):
	try:
		with urllib.request.urlopen(url) as response:
			with open(path, "wb") as outfile:
				shutil.copyfileobj(response, outfile)
	except:
		print("Failed to download ", url)
		raise

def _killproc(name):
	for proc in psutil.process_iter():
		if proc.name() == name:
			proc.kill()

def _setupNgrok(token, region):
	if not os.path.isfile("./ngrok"):
		_log("Downloading ngrok...")
		_download("https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip", "ngrok.zip")
		shutil.unpack_archive("ngrok.zip")
		os.remove("ngrok.zip")
		pathlib.Path("ngrok").chmod(stat.S_IXUSR)
	else:
		_killproc("ngrok")
	
	ngrok_config = "/root/.ngrok2/ngrok.yml"
	subprocess.run(["./ngrok", "authtoken", "-config", ngrok_config, token], check=True)
	
	_log("Creating ngrok tunnel...")
	ngrok_proc = subprocess.Popen(["./ngrok", "tcp", "-config", ngrok_config, "-region", region, "1080"])
	time.sleep(2)
	if ngrok_proc.poll() != None:
		raise RuntimeError("Failed to run ngrok. Return code: {0}\nSee runtime log for more info.".format(ngrok_proc.returncode))
	
	with urllib.request.urlopen("http://localhost:4040/api/tunnels") as response:
		url = json.load(response)["tunnels"][-1]["public_url"]
		index = url.find("://")
		if index != -1:
			url = url[index + len("://"):]
	
	return url, ngrok_proc

def _setupProxy(protocol):
	if not os.path.isfile("./3proxy"):
		_log("Downloading 3proxy...")
		_download("https://raw.githubusercontent.com/LoveEevee/remocolab/master/3proxy.zip", "3proxy.zip")
		shutil.unpack_archive("3proxy.zip")
		os.remove("3proxy.zip")
		pathlib.Path("3proxy").chmod(stat.S_IXUSR)
		pathlib.Path("socks").chmod(stat.S_IXUSR)
		pathlib.Path("proxy").chmod(stat.S_IXUSR)
	else:
		_killproc("3proxy")
	
	proxy3_cfgdir = "/usr/local/etc/3proxy"
	proxy3_cfgfile = os.path.join(proxy3_cfgdir, "3proxy.cfg")
	
	pathlib.Path(proxy3_cfgdir).mkdir(parents=True, exist_ok=True)
	with open(proxy3_cfgfile, "w+") as f:
		proxy_config = [
			"proxy -a -u -n -p1080" if protocol == "HTTP" else "socks -aunp1080"
		]
		f.write("\n".join(proxy_config))
		f.close()
	
	_log("Running the proxy server...")
	proxy3_proc = subprocess.Popen(["./3proxy", proxy3_cfgfile])
	time.sleep(1)
	if proxy3_proc.poll() != None:
		raise RuntimeError("Failed to run 3proxy. Return code: {0}\nSee runtime log for more info.".format(proxy3_proc.returncode))
	
	return proxy3_proc

def setupProxy(token="", region="eu", protocol="SOCKS5"):
	if not token:
		sys.exit("ERROR: Invalid ngrok authtoken. Ensure you have copied the token from https://dashboard.ngrok.com/auth and try again.")
	
	index = region.find(" ")
	if index != -1:
		region = region[:index]
	
	_log("Starting...")
	url, ngrok_proc = _setupNgrok(token, region)
	proxy3_proc = _setupProxy(protocol)
	
	_log("Ready!")
	index = url.find(":")
	print("Protocol: {0}".format(protocol))
	if index != -1:
		print("Server: {0}".format(url[:index]))
		print("Port: {0}".format(url[index+1:]))
	else:
		print("Server: {0}".format(url))
	
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		_log("Exiting...")
		if ngrok_proc.poll() != None:
			ngrok_proc.kill()
		_killproc("ngrok")
		if proxy3_proc.poll() != None:
			proxy3_proc.kill()
		_killproc("3proxy")
