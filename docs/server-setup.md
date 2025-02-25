# Azure Virtual Machine
* Computer name: death-notes-vm
* Operating system: Linux (ubuntu 22.04)
* VM generation: V2
* VM architecture: x64

# Disk
* Size: Standard B2ats v2
* vCPUs: 2
* RAM: 1 GiB


# Setting up Virtual Machine
## Pre-requisites
```
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose nginx -y
sudo systemctl enable --now docker
sudo mkdir -p /opt/data
cd /opt/data/
```

## Add environment variables
```
sudo nano .env
```

## Start application
```
git clone https://github.com/siddydutta/death-notes.git
cd death-notes
cp ../.env .env
sudo docker-compose up -d
```

## Setup NGINX as reverse proxy
```
sudo nano /etc/nginx/sites-available/death-notes
```
<details open>
  <summary>Config</summary>

    server {
        listen 80;
        server_name api.deathnotes.tech deathnotes.uksouth.cloudapp.azure.com;

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
</details>

```
sudo ln -s /etc/nginx/sites-available/death-notes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Enable HTTPS
```
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.deathnotes.tech
sudo crontab -e
```
Add `0 0 * * * certbot renew --quiet`

## Secure server
```
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```


# Monitoring
## Docker Containers
```
cd /opt/data/death-notes
sudo docker ps
sudo docker-compose logs -f
sudo docker-compose exec web python manage.py createsuperuser
```

## Application Logs
```
sudo tail -n 100 -f /opt/data/death-notes/logs/app.log
sudo tail -n 100 -f /opt/data/death-notes/logs/tasks.log
```

## NGINX logs
```
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```
