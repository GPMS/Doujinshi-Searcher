from hitomi import Doujinshi, Config

config = Config()

doujin = Doujinshi()
doujin.artists = [
    "eb110ss",
    "hatomugi munmun",
    "highlow",
    "hikoma hiroyuki",
    "kudou hisashi",
    "kurebayashi asami",
    "matsumoto kichidi",
    "mdo-h",
    "momoyama hato",
    "neriume",
    "rico",
    "rondonko",
    "ronrinri ronri",
    "sabaku",
    "usakun",
    "yawaraka midori"
]

print(doujin.can_add(config))
