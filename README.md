# Ace-Hackathon
The project is Built using the OpenStack SDK for Python and for database we have used MongoDB for storing the user Queries. The repository contains the codes for the project

# 🔧 OpenStack Cloud Automation Toolkit

Automate and manage your OpenStack cloud infrastructure using Python and OpenStack SDK. This toolkit provides utilities for networking, server lifecycle, and key pair management — all designed to streamline cloud operations.

---

## 📦 Features

- ✅ Create and delete OpenStack networks and subnets
- ✅ Launch virtual machines with key pair access
- ✅ Resize VMs dynamically
- ✅ Auto-generate SSH key pairs
- ✅ User-configurable parameters using `.env`

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/openstack-cloud-automation.git
cd openstack-cloud-automation
```

### 2.Create and Activate Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

### 3.Install Dependencies
```bash
pip install -r requirements.txt

```
### 4.Setup Environment Variables
```bash
//Create a .env file in the root directory with the following content:
OPENSTACK_AUTH_URL=https://your-openstack-url:5000
OPENSTACK_USERNAME=your-username
OPENSTACK_PASSWORD=your-password
OPENSTACK_PROJECT_NAME=your-project
OPENSTACK_USER_DOMAIN_NAME=Default
OPENSTACK_PROJECT_DOMAIN_NAME=Default
```

### 5. Youtube video link  - https://youtu.be/7jE-FUFkK9E

