banned_sites="banned_sites"

if [-a $banned_sites]
then
    echo "banned_sites already exists"
else
    touch $banned_sites
    echo "***" > $banned_sites
    echo "banned_sites created"
    echo "usage: put site hostname to banned_sites"
    echo "anything after *** will not be read"
fi
