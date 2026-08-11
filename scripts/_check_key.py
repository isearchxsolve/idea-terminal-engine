import os
v = os.environ.get("STORAGE_ENCRYPTION_KEY")
print("current env STORAGE_ENCRYPTION_KEY:", "set len=" + str(len(v)) if v else "unset")
