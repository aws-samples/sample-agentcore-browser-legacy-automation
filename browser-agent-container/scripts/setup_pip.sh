#!/bin/sh
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Configure pip.conf for enterprise environments with private repositories.

OPTIONS:
    -t, --token-name NAME       SCM token name for authentication
    -s, --token-secret SECRET   SCM token secret for authentication
    -e, --extra-index URLS      Comma-separated list of extra-index-url entries
    -h, --trusted-hosts HOSTS   Comma-separated list of trusted-host entries
    -c, --config "KEY=VALUE"    Additional pip configuration (can be used multiple times)
    --help                      Show this help message

EXAMPLES:
    # Enterprise artifactory with authentication
    $0 -t mytoken -s mysecret -e "https://my.artifactory.com/pypi/simple" -h "my.artifactory.com"

    # Multiple repositories with custom config
    $0 -e "https://repo1.com/simple,https://repo2.com/simple" -c "timeout=60" -c "retries=3"

    # Simple extra index without authentication
    $0 -e "https://pypi.company.com/simple" -h "pypi.company.com"

EOF
}

# Initialize variables
token_name=""
token_secret=""
extra_index_urls=""
trusted_hosts=""
additional_config=""

# Parse command line arguments
while [ $# -gt 0 ]; do
    case $1 in
        -t|--token-name)
            token_name="$2"
            shift 2
            ;;
        -s|--token-secret)
            token_secret="$2"
            shift 2
            ;;
        -e|--extra-index)
            extra_index_urls="$2"
            shift 2
            ;;
        -h|--trusted-hosts)
            trusted_hosts="$2"
            shift 2
            ;;
        -c|--config)
            additional_config="${additional_config}$2\n"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if we have any configuration to write
if [ -z "$extra_index_urls" ] && [ -z "$trusted_hosts" ] && [ -z "$additional_config" ]; then
    echo "No pip configuration specified - skipping pip.conf creation"
    exit 0
fi

# Check if /etc/pip.conf already exists
if [ -f "/etc/pip.conf" ]; then
    echo "Warning: /etc/pip.conf already exists. Backing up to /etc/pip.conf.backup"
    cp /etc/pip.conf /etc/pip.conf.backup
fi

# Start writing pip.conf
echo "Creating /etc/pip.conf..."
cat > /etc/pip.conf << 'EOF'
[global]
EOF

# Add extra-index-url entries
if [ -n "$extra_index_urls" ]; then
    echo "extra-index-url=" >> /etc/pip.conf
    IFS=','
    for url in $extra_index_urls; do
        if [ -n "$token_name" ] && [ -n "$token_secret" ]; then
            echo "    https://${token_name}:${token_secret}@${url#https://}" >> /etc/pip.conf
        else
            echo "    $url" >> /etc/pip.conf
        fi
    done
    unset IFS
fi

# Add trusted-host entries
if [ -n "$trusted_hosts" ]; then
    echo "trusted-host=" >> /etc/pip.conf
    IFS=','
    for host in $trusted_hosts; do
        echo "    $host" >> /etc/pip.conf
    done
    unset IFS
fi

# Add additional configuration
if [ -n "$additional_config" ]; then
    printf "$additional_config" >> /etc/pip.conf
fi

echo "/etc/pip.conf created successfully"
echo "Configuration:"
cat /etc/pip.conf
