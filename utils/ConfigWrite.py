import json

def write_json(data,path="config/config.json"):
    with open(path,"w") as f:
        json.dump(data,f)
    print("file write is successful")
