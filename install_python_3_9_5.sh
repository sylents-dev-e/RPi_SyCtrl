#!/bin/sh

# @jwa

sudo apt update

echo "... install essential packages for compiling source code."
sudo apt install wget build-essential checkinstall
sudo apt install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev liblzma-dev

echo "...  Download the Python 3.9.5 source code from the official download site"
wget https://www.python.org/ftp/python/3.9.5/Python-3.9.5.tar.xz

echo "... unpack the file"
tar -Jxf Python-3.9.5.tar.xz

cd Python-3.9.5
./configure --enable-optimizations

echo "...  compile the source, it?s a good time to get a coffee and a good book."
make

echo "...  replaces your previous Python installation!!"
sudo make install

cd ..
sudo rm -r Python-3.9.5
rm -rf Python-3.9.5.tar.xz*

python --version

echo "# python 3.9 " >> ~/.bashrc
echo "alias python='/usr/local/bin/python3.9'" >> ~/.bashrc
echo "alias pip='/usr/local/bin/pip3.9'" >> ~/.bashrc
# echo "alias pip=pip3" >> ~/.bashrc

. ~/.bashrc		# maybe use source
