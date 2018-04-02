# drc

immature, homebrew irc → discord bridge written in python using:

* [curious](https://github.com/Fuyukai/curious/tree/0.7)
* [trio](https://trio.readthedocs.io/en/latest/index.html)
* [multio](https://github.com/theelous3/multio)

## configuring

```yaml
irc:
  host: my.irc.server
  port: 6667
  autojoin:
    - '#general'
    - '#judgement-hall'
    - '#chocolate-factory'
  nick: o_o
  # nickserv password to be used. registration and identification is automatic.
  password: 'i am watching you'
  # nickserv email to be used. ditto
  email: person@earth
discord:
  token: '...'
  broadcast_channel: ... # channel id

```

## todo

* discord → irc
