###########
# IMPORTS #
###########
import socket
import sys, time
import glob, json
import subprocess


####################
# GLOBAL VARIABLES #
####################
result_path = "results.json"
results = []


####################
# HELPER FUNCTIONS #
####################  
def test(cmds_input, expected_output):
  data_sock = socket.socket()

  IP = "localhost"
  if len(sys.argv) < 2:
    SERVER_PORT = 5217

  SERVER_PORT = int(sys.argv[1])
  subprocess.run("bash kill_server.sh", shell=True)
  subprocess.run(f"python3 server.py {SERVER_PORT} &", shell=True)
  
  time.sleep(0.1)
  data_sock.connect((IP,SERVER_PORT))
  
  actual_output = []
  for cmd in cmds_input:
    data_sock.sendall(bytes(cmd, encoding='utf-8'))
    ret = str(data_sock.recv(1024),encoding='utf-8')
    actual_output.append(ret)
  data_sock.close()

  # Behaviour matches - all outputs are equivalent to values in out files 
  if actual_output == expected_output:
    return True

  else:
    print(actual_output)
    print('-'*20)
    print(expected_output)
    print('='*20)
    return False


##########
# DRIVER #
##########
def tester():
  test_files = glob.glob("tests/**/*.*", recursive=True)
  print(test_files)
  
  test_num = len(test_files)//2
  passed_num = 0
  i = 0
  while i < len (test_files):
    with open(test_files[i]) as f:
      cmds_input = f.readlines()

    with open(test_files[i+1]) as f:
      expected_output = f.readlines()

    test_name = test_files[i].split('/')[-2]
    print(test_name)

    if test(cmds_input, expected_output):
      results.append({test_name:"Passed"})
      passed_num += 1
    else:
      results.append({test_name:"Failed"})
    i += 2
  
  print('#'*10, f"passed {passed_num}/{test_num} tests", '#'*10)
  with open(result_path, 'w') as f:
    json.dump(results, f)


if __name__ == "__main__":
  tester()