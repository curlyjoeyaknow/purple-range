# Negative fixture for rule `unpinned-box-version`.
# The box carries an explicit box_version pin in the same file/block, so the
# gate MUST NOT flag it. A false positive here would block every legitimate
# pinned Vagrant box.
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.box_version = "202407.23.0"
  config.vm.hostname = "victim"
end
