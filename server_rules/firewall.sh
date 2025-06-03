#!/bin/bash

# Limpar regras anteriores
nft flush ruleset

# Criar tabelas
nft add table ip filter
nft add table ip nat

# Criar chains principais
nft add chain ip filter input { type filter hook input priority 0 \; policy drop \; }
nft add chain ip filter forward { type filter hook forward priority 0 \; policy drop \; }
nft add chain ip filter output { type filter hook output priority 0 \; policy accept \; }

nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }

# Permitir tráfego local (loopback)
nft add rule ip filter input iif lo accept

# Permitir conexões estabelecidas e relacionadas
nft add rule ip filter input ct state established,related accept
nft add rule ip filter forward ct state established,related accept

# Permitir SSH apenas da rede interna
nft add rule ip filter input iif enp0s3 ip saddr 192.168.200.0/24 tcp dport 22 accept

# Permitir tráfego web (container WEB nas portas 80 e 443)
nft add rule ip filter input tcp dport 80 accept
nft add rule ip filter input tcp dport 443 accept

# Permitir tráfego OpenVPN (UDP 1194)
nft add rule ip filter input udp dport 1194 accept

# Permitir VPN → LAN (tun0 → enp0s3)
nft add rule ip filter forward iifname "tun0" oifname "enp0s3" accept
nft add rule ip filter forward iifname "enp0s3" oifname "tun0" ct state established,related accept

# Masquerade tráfego VPN para que seja aceito na LAN
nft add rule ip nat postrouting ip saddr 10.8.0.0/24 oifname "enp0s3" masquerade
