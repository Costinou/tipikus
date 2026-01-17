# For server management (Nginx + HTTPS)


```bash
sudo tee /etc/nginx/sites-available/tipikus > /dev/null << EOF
upstream tipikus_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name tipikus.fun www.tipikus.fun;
    
    access_log /var/log/nginx/tipikus-access.log;
    error_log /var/log/nginx/tipikus-error.log;
    
    client_max_body_size 10M;
    root /opt/tipikus;
    
    location /static/ {
        alias /opt/tipikus/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location = /service-worker.js {
        proxy_pass http://tipikus_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    
    location /.well-known/ {
        proxy_pass http://tipikus_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location / {
        proxy_pass http://tipikus_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
```

```bash
log_info "Création du service systemd..."
sudo tee /etc/systemd/system/tipikus.service > /dev/null << EOF
[Unit]
Description=Gunicorn instance to serve Tipikus
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=/opt/tipikus
Environment="PATH=/opt/tipikus/venv/bin"
ExecStart=/opt/tipikus/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10
StandardOutput=append:/var/log/tipikus/gunicorn-stdout.log
StandardError=append:/var/log/tipikus/gunicorn-stderr.log

[Install]
WantedBy=multi-user.target
EOF
```


```bash
log_info "Démarrage des services..."
sudo systemctl daemon-reload
sudo systemctl enable tipikus
sudo systemctl start tipikus
sudo systemctl reload nginx


log_info "Configuration du firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```


```bash
log_info "Installation du certificat SSL avec Let's Encrypt..."
log_warn "Assurez-vous que votre domaine pointe vers ce serveur !"
read -p "Installer le certificat SSL maintenant ? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --register-unsafely-without-email || log_warn "Erreur SSL, vous pouvez le faire manuellement plus tard"
fi

log_info "Vérification du statut..."
sudo systemctl status tipikus --no-pager -l
sudo systemctl status nginx --no-pager -l
```