*/5 * * * *     swift   test -x /usr/bin/swift-recon-cron && test -r /etc/swift/object-server.conf && /usr/bin/swift-recon-cron /etc/swift/object-server.conf
