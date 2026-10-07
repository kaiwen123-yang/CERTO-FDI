"""Real Windows sharing-conflict regression; no scientific computation."""
import json
import os
from pathlib import Path
import threading
import time
import d2a_cert_batch as batch
import d2a_cert_case as core
import d2a_cert_publish_live as publisher

folder=batch.WORK/"d2a_cert_atomic_retry_fixture";folder.mkdir(exist_ok=True)
results=[]
for name,write in (("batch",lambda path:batch.atomic(path,"new\n")),
                   ("core",lambda path:core.atomic_text(path,"new\n")),
                   ("publisher",lambda path:publisher.atomic(path,{"value":"new"}))):
    target=folder/(name+".json");target.write_bytes(b"old\n")
    reader=target.open("rb")
    release=threading.Thread(target=lambda:(time.sleep(.25),reader.close()));release.start()
    start=time.monotonic();write(target);elapsed=time.monotonic()-start;release.join()
    assert elapsed>=.20 and b"new" in target.read_bytes()
    results.append({"function":name,"actual_windows_reader_conflict_recovered":True,"elapsed_seconds":elapsed,"temp_retained_after_success":target.with_name(target.name+".next").exists()})
receipt={"checks":results,"scientific_recursions":0,"production_files_modified":False}
batch.atomic(batch.WORK/"d2a_cert_atomic_retry_fixture_results.json",json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt),flush=True)
