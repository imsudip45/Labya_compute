FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y openssh-server sudo python3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd
# Create user
RUN useradd -m -s /bin/bash labuser && echo 'labuser:changeme' | chpasswd && adduser labuser sudo
# Enable password auth
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
EXPOSE 22
CMD ["/usr/sbin/sshd","-D"]
