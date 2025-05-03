import re
import spacy

nlp = spacy.load("en_core_web_sm")

def parse_intent(message):
    doc = nlp(message.lower())
    message_original = message.strip()

    intent = None
    params = {}

    # Normalize message
    msg = message_original.lower()

    # Synonyms for common cloud terms (VM, server, instance, volume, network)
    vm_keywords = ["vm", "server", "machine", "instance", "compute"]
    network_keywords = ["network", "vpc", "subnet", "cloud network"]
    volume_keywords = ["volume", "disk", "storage"]

    # Match: Create VM
    if "create" in msg and any(word in msg for word in vm_keywords):
        intent = "create_vm"
        
        # Improved regex for flavor (handling "where flavor is" syntax)
        match_flavor = re.search(r"(?:flavor|flavour|size|type)\s*(?::?\s*|\s*is\s*)?([a-zA-Z0-9\-\.]+)", msg, re.I)

        # Match 'named <name>', 'create vm <name>', or 'create <name>'
        match_name = re.search(r"(?:named\s+|create\s+(?:vm|server|machine|instance|compute)\s*|\s*name\s*)([\w\.-]+)", msg, re.I)

        if match_flavor:
            params["flavor"] = match_flavor.group(1).upper()
        if match_name:
            params["name"] = match_name.group(1)

        missing = []
        if "flavor" not in params:
            missing.append("flavor (e.g., S.4, M.8)")
        if "name" not in params:
            missing.append("VM name")
        if missing:
            params["missing"] = missing

    # Match: Resize VM
    elif "resize" in msg and any(word in msg for word in vm_keywords):
        intent = "resize_vm"
        match_flavor = re.search(r"(?:flavor|flavour|size|type)\s*(?::?\s*|\s*is\s*)?([smg]\.\d+)", msg, re.I)
        match_name = re.search(r"resize\s+([\w\.-]+)\s+to", msg, re.I)

        if match_name:
            params["name"] = match_name.group(1)
        if match_flavor:
            params["flavor"] = match_flavor.group(1).upper()

        missing = []
        if "name" not in params:
            missing.append("VM name")
        if "flavor" not in params:
            missing.append("flavor")
        if missing:
            params["missing"] = missing

    # Match: Delete VM
    elif "delete" in msg and any(word in msg for word in vm_keywords):
        intent = "delete_vm"
        match_name = re.search(r"(?:vm|server|machine|instance)\s+([\w\.-]+)", msg, re.I)
        if match_name:
            params["name"] = match_name.group(1)
        else:
            params["missing"] = ["VM name"]

    # Match: Create Network
    elif "create" in msg and any(word in msg for word in network_keywords):
        intent = "create_network"
        match_name = re.search(r"called\s+([\w\.-]+)", msg, re.I)
        if match_name:
            params["name"] = match_name.group(1).strip(".,")
        else:
            params["missing"] = ["network name"]

    # Match: Delete Network
    elif "delete" in msg and any(word in msg for word in network_keywords):
        intent = "delete_network"
        match_name = re.search(r"network\s+([\w\.-]+)", msg, re.I)
        if match_name:
            params["name"] = match_name.group(1)
        else:
            params["missing"] = ["network name"]

    # Match: Create Volume
    elif "create" in msg and any(word in msg for word in volume_keywords):
        intent = "create_volume"
        match_size = re.search(r"(\d+)\s*gb|\s*([0-9]+[m|g|t]{1}b)?", msg, re.I)  # Handle GB, MB, or TB
        match_name = re.search(r"named\s+([\w\.-]+)", msg, re.I)

        if match_size:
            params["size"] = int(match_size.group(1))  # Convert to integer
        if match_name:
            params["name"] = match_name.group(1)

        missing = []
        if "name" not in params:
            missing.append("volume name")
        if "size" not in params:
            missing.append("volume size")
        if missing:
            params["missing"] = missing

    # Match: Delete Volume
    elif "delete" in msg and any(word in msg for word in volume_keywords):
        intent = "delete_volume"
        match_name = re.search(r"volume\s+([\w\.-]+)", msg, re.I)
        if match_name:
            params["name"] = match_name.group(1)
        else:
            params["missing"] = ["volume name"]

    # Match: Usage Query
    elif "usage" in msg or "project usage" in msg:
        intent = "usage_query"

    else:
        intent = "unknown"
        params["details"] = "Intent not recognized."

    params["intent"] = intent
    return params