*/5 * * * *     swift   test -x /usr/bin/swift-drive-audit && test -r /etc/swift/drive-audit.conf && /usr/bin/swift-drive-audit /etc/swift/drive-audit.conf
