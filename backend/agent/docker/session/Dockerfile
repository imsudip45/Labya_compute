FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y openssh-server sudo python3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd
# Create user
# No password until the agent sets the session's own one (an unset password can't log in).
RUN useradd -m -s /bin/bash labuser && adduser labuser sudo
# Enable password auth
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
EXPOSE 22
CMD ["/usr/sbin/sshd","-D"]
