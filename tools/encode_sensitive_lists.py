import base64
import zlib

K = bytes([0x53, 0x50, 0x42, 0x2D, 0x4B, 0x45, 0x59, 0x21,
           0x40, 0x23, 0x24, 0x25, 0x5E, 0x26, 0x2A, 0x28])

def enc(plain: str) -> str:
    raw = plain.encode("utf-8")
    xored = bytes(b ^ K[i % len(K)] for i, b in enumerate(raw))
    return base64.b64encode(zlib.compress(xored)).decode("ascii")

adult = "pornhub.com,xvideos.com,xnxx.com,xhamster.com,chaturbate.com,livejasmin.com,cam4.com,myfreecams.com,stripchat.com,bongacams.com,brazzers.com,bangbros.com,onlyfans.com,fapello.com,redtube.com"
gamble = "bet365.com,draftkings.com,fanduel.com,bovada.lv,betway.com,williamhill.com,pokerstars.com,888casino.com,betfair.com,unibet.com,caesarscasino.com,mgmresorts.com,betmgm.com"
piracy = "thepiratebay.org,1337x.to,rutracker.org,fitgirl-repacks.site,nyaa.si,rarbg.to,kickasstorrents.to,torrentz2.eu,yts.mx,eztv.re,limetorrents.cc,isozone.net,crackedgames.net,skidrowreloaded.com,repack-games.com"

print(enc(adult))
print(enc(gamble))
print(enc(piracy))
