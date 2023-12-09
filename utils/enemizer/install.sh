PLATFORM=$(uname -s)

# if we're on linux, download the linux version of the enemizer
if [ "$PLATFORM" = "Linux" ]; then
    curl https://github.com/tcprescott/Enimizer/releases/download/2mb-rom/ubuntu.16.04-x64.tar.gz -o ubuntu.16.04-x64.tar.gz -L
    mkdir ubuntu.16.04-x64
    tar -xzf ubuntu.16.04-x64.tar.gz -C ubuntu.16.04-x64
fi

if [ "$PLATFORM" = "Darwin" ]; then
    curl https://github.com/tcprescott/Enimizer/releases/download/2mb-rom/osx.10.12-x64.tar.gz -o osx.10.12-x64.tar.gz -L
    mkdir osx.10.12-x64
    tar -xzf osx.10.12-x64.tar.gz -C osx.10.12-x64
fi