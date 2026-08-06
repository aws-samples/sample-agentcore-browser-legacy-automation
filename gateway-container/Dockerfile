# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Apply latest Amazon Linux 2023 security patches before installing extras.
# AL2023 receives ALAS security updates through June 2029; rebuilding (or
# pinning to a digest) picks up new CVE fixes automatically. nginx is
# available from the default AL2023 repo (no EPEL or extras needed).
RUN dnf -y upgrade --releasever=latest && \
    dnf -y install nginx gettext && \
    dnf clean all && rm -rf /var/cache/dnf

# Remove default nginx config — our envsubst-rendered nginx.conf takes over.
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy NGINX config template and entrypoint
COPY nginx/nginx.conf /etc/nginx/templates/nginx.conf.template
COPY nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

# AL2023 ships curl-minimal (not wget), so the healthcheck uses curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
