#!/usr/bin/env python3
"""Patch Vril's Android build with the Xziel Cloudflare datagram tunnel.

The original Quake/NZ:P datagram protocol remains authoritative. Only the SDL
UDP transport is intercepted for virtual 10.77.0.<player-slot> addresses while
an Xziel online room is active.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_multiplayer_online.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit("Could not find " + label)
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Main menu: use the formerly-grey cooperative slot as the room entry point.
# ---------------------------------------------------------------------------
main = source / "menu" / "menu_main.c"
text = main.read_text(encoding="utf-8")
resume_anchor = """#ifdef __ANDROID__
static qboolean Menu_XzielResumeExists(void)
"""
if "Menu_XzielMultiplayer" not in text:
    bridge = """#ifdef __ANDROID__
extern void Xziel_Android_OpenMultiplayer(void);

static void Menu_XzielMultiplayer(void)
{
    Xziel_Android_OpenMultiplayer();
}
#endif

"""
    text = replace_once(text, resume_anchor, bridge + resume_anchor,
                        "Android main-menu anchor")

old = """		Menu_DrawButton(1 + xziel_offset, xziel_offset, "SOLO", "Play Solo.", Menu_Solo);
		Menu_DrawGreyButton(2 + xziel_offset, "COOPERATIVE");

		Menu_DrawDivider(3 + xziel_offset);
"""
new = """		Menu_DrawButton(1 + xziel_offset, xziel_offset, "SOLO", "Play Solo.", Menu_Solo);
		Menu_DrawButton(2 + xziel_offset, 1 + xziel_offset, "MULTIPLAYER", "Create or join a private internet room.", Menu_XzielMultiplayer);

		Menu_DrawDivider(3 + xziel_offset);
"""
if old in text:
    text = text.replace(old, new, 1)

# Shift the following Android buttons down one logical selector slot.
text = text.replace(
    'Menu_DrawButton(3 + xziel_offset, 1 + xziel_offset, "CONFIGURATION"',
    'Menu_DrawButton(3 + xziel_offset, 2 + xziel_offset, "CONFIGURATION"',
    1)
text = text.replace(
    'Menu_DrawButton(4 + xziel_offset, 2 + xziel_offset, "CHARACTER BIOS"',
    'Menu_DrawButton(4 + xziel_offset, 3 + xziel_offset, "CHARACTER BIOS"',
    1)
text = text.replace(
    'Menu_DrawButton(5 + xziel_offset, 3 + xziel_offset, "CREDITS"',
    'Menu_DrawButton(5 + xziel_offset, 4 + xziel_offset, "CREDITS"',
    1)
text = text.replace(
    'Menu_DrawButton(6 + xziel_offset, 4 + xziel_offset, "QUIT GAME"',
    'Menu_DrawButton(6 + xziel_offset, 5 + xziel_offset, "QUIT GAME"',
    1)
main.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Host frame: UI/network threads never call Cbuf directly. Android deposits
# commands and the game thread consumes them here before Cbuf_Execute().
# ---------------------------------------------------------------------------
host = source / "host.c"
text = host.read_text(encoding="utf-8")
platform_anchor = """#ifdef PLATFORM_SDL
extern qboolean sdl_running;
#endif
"""
online_decl = """#ifdef __ANDROID__
extern int Xziel_Android_OnlinePollCommand(char *out, int outSize);
#endif
"""
if "Xziel_Android_OnlinePollCommand" not in text:
    text = replace_once(text, platform_anchor, platform_anchor + online_decl,
                        "host Android declaration anchor")

execute_anchor = """// process console commands
	Cbuf_Execute ();
"""
execute_repl = """// process console commands
#ifdef __ANDROID__
	{
		char xziel_online_command[512];
		if (Xziel_Android_OnlinePollCommand(
			xziel_online_command, sizeof(xziel_online_command)))
			Cbuf_AddText(xziel_online_command);
	}
#endif
	Cbuf_Execute ();
"""
if "char xziel_online_command[512]" not in text:
    text = replace_once(text, execute_anchor, execute_repl,
                        "host command execution anchor")
host.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# SDL UDP: virtual internet peers are 10.77.0.<slot>. OS UDP remains untouched
# for normal solo/LAN operation and for local socket allocation/port identity.
# ---------------------------------------------------------------------------
udp = source / "platform" / "sdl" / "net_udp_sdl.c"
text = udp.read_text(encoding="utf-8")
include_anchor = '#include <unistd.h>\n\n'
decls = r'''#ifdef __ANDROID__
extern int Xziel_Android_OnlineActive(void);
extern int Xziel_Android_GameHasPacket(int localPort);
extern int Xziel_Android_GameSend(const unsigned char *data, int len,
    int destinationSlot, int sourcePort, int destinationPort);
extern int Xziel_Android_GamePoll(int localPort, unsigned char *out, int maxLen,
    int *sourceSlot, int *sourcePort);

#define XZIEL_VIRTUAL_NET 0x0A4D0000u

static int Xziel_SocketPort(int socket_fd)
{
    struct sockaddr_in address;
    socklen_t len = sizeof(address);
    if (getsockname(socket_fd, (struct sockaddr *)&address, &len) == -1)
        return 0;
    return ntohs(address.sin_port);
}

static int Xziel_VirtualSlot(const struct qsockaddr *addr)
{
    unsigned int host;
    if (!addr || addr->sa_family != AF_INET)
        return 0;
    host = ntohl(((const struct sockaddr_in *)addr)->sin_addr.s_addr);
    if ((host & 0xFFFFFF00u) != XZIEL_VIRTUAL_NET)
        return 0;
    host &= 0xFFu;
    return (host >= 1u && host <= 4u) ? (int)host : 0;
}

static void Xziel_SetVirtualAddr(struct qsockaddr *addr, int slot, int port)
{
    struct sockaddr_in *internet = (struct sockaddr_in *)addr;
    memset(addr, 0, sizeof(*addr));
    internet->sin_family = AF_INET;
    internet->sin_addr.s_addr = htonl(XZIEL_VIRTUAL_NET | (unsigned int)slot);
    internet->sin_port = htons((unsigned short)port);
}
#endif

'''
if "XZIEL_VIRTUAL_NET" not in text:
    text = replace_once(text, include_anchor, include_anchor + decls,
                        "UDP include anchor")

old_check = r'''int UDP_CheckNewConnections (void)
{
	char buf[4096];
	
	if (net_acceptsocket == -1)
		return -1;

	if (recvfrom(net_acceptsocket, buf, 4096, MSG_PEEK, NULL, NULL) > 0)
		return net_acceptsocket;
		
	return -1;
}'''
new_check = r'''int UDP_CheckNewConnections (void)
{
	char buf[4096];

	if (net_acceptsocket == -1)
		return -1;

#ifdef __ANDROID__
	if (Xziel_Android_OnlineActive()) {
		int local_port = Xziel_SocketPort(net_acceptsocket);
		if (local_port > 0 && Xziel_Android_GameHasPacket(local_port))
			return net_acceptsocket;
	}
#endif

	if (recvfrom(net_acceptsocket, buf, 4096, MSG_PEEK, NULL, NULL) > 0)
		return net_acceptsocket;

	return -1;
}'''
text = replace_once(text, old_check, new_check, "UDP_CheckNewConnections")

old_read = r'''int UDP_Read (int socket, byte *buf, int len, struct qsockaddr *addr)
{
	int addrlen = sizeof (struct qsockaddr);
	int ret;

	ret = recvfrom(socket, (char *)buf, len, 0, (struct sockaddr *)addr, (socklen_t*)&addrlen);
	if (ret == -1 )
		return 0;
	return ret;
}'''
new_read = r'''int UDP_Read (int socket, byte *buf, int len, struct qsockaddr *addr)
{
	int addrlen = sizeof (struct qsockaddr);
	int ret;

#ifdef __ANDROID__
	if (Xziel_Android_OnlineActive()) {
		int local_port = Xziel_SocketPort(socket);
		int source_slot = 0;
		int source_port = 0;
		if (local_port > 0) {
			ret = Xziel_Android_GamePoll(local_port, buf, len,
				&source_slot, &source_port);
			if (ret > 0 && source_slot >= 1 && source_slot <= 4) {
				Xziel_SetVirtualAddr(addr, source_slot, source_port);
				return ret;
			}
		}
	}
#endif

	ret = recvfrom(socket, (char *)buf, len, 0,
		(struct sockaddr *)addr, (socklen_t*)&addrlen);
	if (ret == -1 )
		return 0;
	return ret;
}'''
text = replace_once(text, old_read, new_read, "UDP_Read")

old_write = r'''int UDP_Write (int socket, byte *buf, int len, struct qsockaddr *addr)
{
	int ret;

	ret = sendto (socket, (const char *)buf, len, 0, (struct sockaddr *)addr, sizeof(struct qsockaddr));
	if (ret == -1 )
		return 0;
	return ret;
}'''
new_write = r'''int UDP_Write (int socket, byte *buf, int len, struct qsockaddr *addr)
{
	int ret;

#ifdef __ANDROID__
	if (Xziel_Android_OnlineActive()) {
		int destination_slot = Xziel_VirtualSlot(addr);
		if (destination_slot) {
			int source_port = Xziel_SocketPort(socket);
			int destination_port =
				ntohs(((struct sockaddr_in *)addr)->sin_port);
			if (source_port > 0 &&
				Xziel_Android_GameSend(buf, len, destination_slot,
					source_port, destination_port))
				return len;
			return 0;
		}
	}
#endif

	ret = sendto (socket, (const char *)buf, len, 0,
		(struct sockaddr *)addr, sizeof(struct qsockaddr));
	if (ret == -1 )
		return 0;
	return ret;
}'''
text = replace_once(text, old_write, new_write, "UDP_Write")
udp.write_text(text, encoding="utf-8")

print("Xziel multiplayer internet tunnel patch applied.")
