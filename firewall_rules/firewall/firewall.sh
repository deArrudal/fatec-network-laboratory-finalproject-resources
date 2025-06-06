#!/bin/bash

# Limpar configurações antigas
nft flush ruleset

# Criar tabelas
nft add table ip filter
nft add table ip nat

# Criar chains na tabela filter
nft add chain ip filter input { type filter hook input priority 0 \; policy drop \; }
nft add chain ip filter forward { type filter hook forward priority 0 \; policy drop \; }
nft add chain ip filter output { type filter hook output priority 0 \; policy accept \; }

# Criar chains na tabela nat
nft add chain ip nat prerouting { type nat hook prerouting priority -100 \; }
nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }

# Permitir tráfego local (loopback)
nft add rule ip filter input iif lo accept

# Permitir tráfego estabelecido e relacionado
nft add rule ip filter input ct state established,related accept
nft add rule ip filter forward ct state established,related accept

# Redirecionar HTTP (porta 80) para HTTPS no container WEB
nft add rule ip nat prerouting iif enp0s3 tcp dport 80 dnat to 192.168.200.4:443
nft add rule ip filter forward iif enp0s3 ip daddr 192.168.200.4 tcp dport 443 accept

# HTTPS (443) direto para container WEB
nft add rule ip nat prerouting iif enp0s3 tcp dport 443 dnat to 192.168.200.4:443
nft add rule ip filter forward iif enp0s3 ip daddr 192.168.200.4 tcp dport 443 accept

# Permitir OpenVPN (UDP 1194) para o servidor VPN
nft add rule ip nat prerouting iif enp0s3 udp dport 1194 dnat to 192.168.200.4:1194
nft add rule ip filter forward iif enp0s3 ip daddr 192.168.200.4 udp dport 1194 accept

# Permitir manutenção SSH (porta 22) APENAS da rede interna
nft add rule ip filter input iif enp0s8 ip saddr 192.168.200.0/24 tcp dport 22 accept

# Bloquear qualquer outro tráfego da Internet (enp0s3) para a rede interna
nft add rule ip filter forward iif enp0s3 ip daddr 192.168.200.0/24 drop

# NAT de saída se necessário para clientes internos acessarem a Internet
nft add rule ip nat postrouting oif enp0s3 ip saddr 192.168.200.0/24 masquerade
