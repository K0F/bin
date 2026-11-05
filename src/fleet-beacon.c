/* =============================================================================
 * fleet-beacon.c — Multi-node Realtime Telemetry Beacon (Pure C POSIX)
 * Observatoř Telemetry Platform // Fleet Operations
 *
 * Broadcasts UDP telemetry packets (port 9850) every 1.5s.
 * Zero runtime dependencies, minimal RAM (< 1MB), 0.00% idle CPU.
 * =============================================================================
 */

#define _POSIX_C_SOURCE 200809L
#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/statvfs.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <time.h>
#include <glob.h>
#include <fcntl.h>
#include <errno.h>

#define BEACON_PORT 9850
#define INTERVAL_US 1500000

static const char *TARGETS[] = {
    "255.255.255.255",
    "192.168.1.255",
    "192.168.1.100",  /* t520 ETH */
    "192.168.1.102",  /* t520 WiFi */
    "192.168.1.104",  /* bazina */
    "192.168.1.101",  /* boxC */
    "192.168.1.105",  /* crostini */
    "192.168.1.103",  /* android */
    "10.39.9.255",    /* WireGuard Broadcast */
    "10.39.9.1",      /* boxC VPN */
    "10.0.0.255",
    "10.0.0.18",
    "10.0.0.14",
    "91.139.118.43",
    "192.168.43.255",
    "192.168.43.1",
    "127.0.0.1",
    NULL
};

static void resolve_identity(char *node, size_t n_len, char *arch, size_t a_len, char *sign, size_t s_len, char *raw_host, size_t h_len) {
    /* 1. Hostname */
    char hbuf[128] = {0};
    if (gethostname(hbuf, sizeof(hbuf) - 1) != 0) {
        snprintf(hbuf, sizeof(hbuf), "unknown");
    }
    char *dot = strchr(hbuf, '.');
    if (dot) *dot = '\0';
    snprintf(raw_host, h_len, "%s", hbuf);

    /* 2. FLEET_NODE override / file probe */
    const char *env_node = getenv("FLEET_NODE");
    if (env_node && *env_node) {
        snprintf(node, n_len, "%s", env_node);
    } else {
        char line[256];
        FILE *fp = fopen("/etc/fleet_id", "r");
        if (!fp) {
            char home_f[256];
            const char *home = getenv("HOME");
            if (home) {
                snprintf(home_f, sizeof(home_f), "%s/.fleet_id", home);
                fp = fopen(home_f, "r");
            }
        }
        if (fp) {
            while (fgets(line, sizeof(line), fp)) {
                char *p = line;
                while (*p == ' ' || *p == '\t') p++;
                if (*p == '#' || *p == '\n' || *p == '\r' || *p == '\0') continue;

                if (strncmp(p, "FLEET_NODE=", 11) == 0) {
                    char *val = p + 11;
                    if (*val == '"' || *val == '\'') val++;
                    size_t l = strlen(val);
                    while (l > 0 && (val[l-1] == '\n' || val[l-1] == '\r' || val[l-1] == '"' || val[l-1] == '\'' || val[l-1] == ' ')) val[--l] = '\0';
                    snprintf(node, n_len, "%s", val);
                } else if (strncmp(p, "FLEET_ARCH=", 11) == 0) {
                    char *val = p + 11;
                    if (*val == '"' || *val == '\'') val++;
                    size_t l = strlen(val);
                    while (l > 0 && (val[l-1] == '\n' || val[l-1] == '\r' || val[l-1] == '"' || val[l-1] == '\'' || val[l-1] == ' ')) val[--l] = '\0';
                    snprintf(arch, a_len, "%s", val);
                } else if (strncmp(p, "FLEET_SIGN=", 11) == 0) {
                    char *val = p + 11;
                    if (*val == '"' || *val == '\'') val++;
                    size_t l = strlen(val);
                    while (l > 0 && (val[l-1] == '\n' || val[l-1] == '\r' || val[l-1] == '"' || val[l-1] == '\'' || val[l-1] == ' ')) val[--l] = '\0';
                    snprintf(sign, s_len, "%s", val);
                } else if (node[0] == '\0') {
                    size_t l = strlen(p);
                    while (l > 0 && (p[l-1] == '\n' || p[l-1] == '\r' || p[l-1] == ' ')) p[--l] = '\0';
                    snprintf(node, n_len, "%s", p);
                }
            }
            fclose(fp);
        }

        if (node[0] == '\0') {
            if (access("/data/data/com.termux", F_OK) == 0 || getenv("TERMUX_VERSION") != NULL) {
                snprintf(node, n_len, "android");
            } else if (strcmp(hbuf, "localhost") == 0 || strcmp(hbuf, "android") == 0) {
                snprintf(node, n_len, "android");
            } else if (strcmp(hbuf, "penguin") == 0) {
                snprintf(node, n_len, "crostini");
            } else {
                snprintf(node, n_len, "%s", hbuf);
            }
        }
    }

    /* 3. Arch */
    const char *env_arch = getenv("FLEET_ARCH");
    if (env_arch && *env_arch) {
        snprintf(arch, a_len, "%s", env_arch);
    } else {
        struct utsname uts;
        if (uname(&uts) == 0) {
            snprintf(arch, a_len, "%s", uts.machine);
        } else {
            snprintf(arch, a_len, "unknown");
        }
    }

    /* 4. Sign */
    const char *env_sign = getenv("FLEET_SIGN");
    if (env_sign && *env_sign) {
        snprintf(sign, s_len, "%s", env_sign);
    } else {
        snprintf(sign, s_len, "[%s:%s]", node, arch);
    }
}

static double read_cpu(unsigned long long *prev_work, unsigned long long *prev_total) {
    FILE *fp = fopen("/proc/stat", "r");
    if (!fp) return 0.0;

    char line[256];
    if (!fgets(line, sizeof(line), fp)) {
        fclose(fp);
        return 0.0;
    }
    fclose(fp);

    unsigned long long user = 0, nice = 0, system = 0, idle = 0, iowait = 0, irq = 0, softirq = 0, steal = 0;
    if (sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
               &user, &nice, &system, &idle, &iowait, &irq, &softirq, &steal) < 4) {
        return 0.0;
    }

    unsigned long long work = user + nice + system + irq + softirq + steal;
    unsigned long long total = work + idle + iowait;

    double pct = 0.0;
    if (*prev_total > 0 && total > *prev_total) {
        unsigned long long d_work = work - *prev_work;
        unsigned long long d_total = total - *prev_total;
        pct = ((double)d_work / (double)d_total) * 100.0;
        if (pct < 0.0) pct = 0.0;
        if (pct > 100.0) pct = 100.0;
    }

    *prev_work = work;
    *prev_total = total;
    return pct;
}

static void read_memory(double *used_gb, double *total_gb) {
    *used_gb = 0.0;
    *total_gb = 0.0;

    FILE *fp = fopen("/proc/meminfo", "r");
    if (!fp) return;

    char line[128];
    double total_kb = 0.0, avail_kb = 0.0, free_kb = 0.0, buffers_kb = 0.0, cached_kb = 0.0;
    int have_avail = 0;

    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "MemTotal:", 9) == 0) {
            sscanf(line + 9, "%lf", &total_kb);
        } else if (strncmp(line, "MemAvailable:", 13) == 0) {
            sscanf(line + 13, "%lf", &avail_kb);
            have_avail = 1;
        } else if (strncmp(line, "MemFree:", 8) == 0) {
            sscanf(line + 8, "%lf", &free_kb);
        } else if (strncmp(line, "Buffers:", 8) == 0) {
            sscanf(line + 8, "%lf", &buffers_kb);
        } else if (strncmp(line, "Cached:", 7) == 0) {
            sscanf(line + 7, "%lf", &cached_kb);
        }
    }
    fclose(fp);

    if (!have_avail) {
        avail_kb = free_kb + buffers_kb + cached_kb;
    }

    *total_gb = total_kb / (1024.0 * 1024.0);
    *used_gb = (total_kb - avail_kb) / (1024.0 * 1024.0);
    if (*used_gb < 0.0) *used_gb = 0.0;
}

static void read_disk(const char *node, char *mount_out, size_t m_len, double *free_gb, double *total_gb) {
    const char *candidates[4] = { "/", NULL, NULL, NULL };

    if (strcmp(node, "boxC") == 0) {
        candidates[0] = "/mnt/kof17";
        candidates[1] = "/";
    } else if (strcmp(node, "bazina") == 0) {
        candidates[0] = "/mnt/ssd";
        candidates[1] = "/mnt/seagate";
        candidates[2] = "/";
    }

    for (int i = 0; candidates[i] != NULL; ++i) {
        struct statvfs st;
        if (statvfs(candidates[i], &st) == 0 && st.f_blocks > 0) {
            snprintf(mount_out, m_len, "%s", candidates[i]);
            *free_gb = ((double)st.f_bavail * (double)st.f_frsize) / (1024.0 * 1024.0 * 1024.0);
            *total_gb = ((double)st.f_blocks * (double)st.f_frsize) / (1024.0 * 1024.0 * 1024.0);
            return;
        }
    }

    snprintf(mount_out, m_len, "/");
    *free_gb = 0.0;
    *total_gb = 0.0;
}

static void read_gpu(char *gpu_out, size_t g_len) {
    gpu_out[0] = '\0';
    glob_t gl;
    if (glob("/sys/class/drm/card*/device/gpu_busy_percent", 0, NULL, &gl) == 0) {
        for (size_t i = 0; i < gl.gl_pathc; ++i) {
            FILE *fp = fopen(gl.gl_pathv[i], "r");
            if (fp) {
                int busy = 0;
                if (fscanf(fp, "%d", &busy) == 1) {
                    snprintf(gpu_out, g_len, "Navi10 %d%%", busy);
                    fclose(fp);
                    break;
                }
                fclose(fp);
            }
        }
        globfree(&gl);
    }
}

static int read_temp(void) {
    const char *paths[] = {
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/hwmon/hwmon0/temp1_input",
        "/sys/class/hwmon/hwmon1/temp1_input",
        NULL
    };
    for (int i = 0; paths[i] != NULL; ++i) {
        FILE *fp = fopen(paths[i], "r");
        if (fp) {
            long temp_raw = 0;
            if (fscanf(fp, "%ld", &temp_raw) == 1) {
                fclose(fp);
                return (int)(temp_raw / 1000);
            }
            fclose(fp);
        }
    }
    return 0;
}

static int read_battery(void) {
    glob_t gl;
    const char *patterns[] = {
        "/sys/class/power_supply/BAT*/capacity",
        "/sys/class/power_supply/*battery*/capacity",
        "/sys/class/power_supply/sbs-*/capacity",
        NULL
    };
    for (int p = 0; patterns[p] != NULL; ++p) {
        if (glob(patterns[p], 0, NULL, &gl) == 0) {
            for (size_t i = 0; i < gl.gl_pathc; ++i) {
                FILE *fp = fopen(gl.gl_pathv[i], "r");
                if (fp) {
                    int cap = -1;
                    if (fscanf(fp, "%d", &cap) == 1) {
                        fclose(fp);
                        globfree(&gl);
                        return cap;
                    }
                    fclose(fp);
                }
            }
            globfree(&gl);
        }
    }
    return -1;
}

static void update_shm(const char *node, const char *payload) {
    const char *shm_path = "/dev/shm/fleet_telemetry.json";
    char tmp_path[256];
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp.%d", shm_path, (int)getpid());

    /* Read existing file up to 64KB */
    char in_buf[65536] = {0};
    FILE *fp = fopen(shm_path, "r");
    if (fp) {
        size_t n = fread(in_buf, 1, sizeof(in_buf) - 1, fp);
        in_buf[n] = '\0';
        fclose(fp);
    }

    FILE *out = fopen(tmp_path, "w");
    if (!out) return;

    /* Write simple JSON envelope */
    if (in_buf[0] == '{') {
        /* Filter out existing node key and append new */
        fprintf(out, "{\n");
        int wrote_any = 0;

        /* Scan and copy other nodes */
        const char *known[] = { "t520", "bazina", "boxC", "crostini", "penguin", "android", "phone", NULL };
        for (int k = 0; known[k] != NULL; ++k) {
            if (strcmp(known[k], node) == 0) continue;
            char needle[64];
            snprintf(needle, sizeof(needle), "\"%s\":", known[k]);
            char *pos = strstr(in_buf, needle);
            if (pos) {
                /* Find opening brace */
                char *brace_start = strchr(pos, '{');
                if (brace_start) {
                    int depth = 1;
                    char *ptr = brace_start + 1;
                    while (*ptr && depth > 0) {
                        if (*ptr == '{') depth++;
                        else if (*ptr == '}') depth--;
                        ptr++;
                    }
                    if (depth == 0) {
                        if (wrote_any) fprintf(out, ",\n");
                        fprintf(out, "  \"%s\": ", known[k]);
                        fwrite(brace_start, 1, (size_t)(ptr - brace_start), out);
                        wrote_any = 1;
                    }
                }
            }
        }

        if (wrote_any) fprintf(out, ",\n");
        fprintf(out, "  \"%s\": %s\n}\n", node, payload);
    } else {
        fprintf(out, "{\n  \"%s\": %s\n}\n", node, payload);
    }

    fclose(out);
    chmod(tmp_path, 0666);
    rename(tmp_path, shm_path);
}

static void send_wan_http(const char *payload) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return;

    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 500000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    struct sockaddr_in srv;
    memset(&srv, 0, sizeof(srv));
    srv.sin_family = AF_INET;
    srv.sin_port = htons(80);
    inet_pton(AF_INET, "91.139.118.43", &srv.sin_addr);

    if (connect(sock, (struct sockaddr *)&srv, sizeof(srv)) == 0) {
        char req[4096];
        int req_len = snprintf(req, sizeof(req),
            "POST /telemetry.php HTTP/1.1\r\n"
            "Host: 91.139.118.43\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: %zu\r\n"
            "Connection: close\r\n\r\n"
            "%s", strlen(payload), payload);
        if (req_len > 0) {
            write(sock, req, (size_t)req_len);
        }
    }
    close(sock);
}

int main(int argc, char **argv) {
    int run_once = 0;
    int print_json = 0;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--once") == 0 || strcmp(argv[i], "-1") == 0) run_once = 1;
        else if (strcmp(argv[i], "--json") == 0 || strcmp(argv[i], "-j") == 0) { run_once = 1; print_json = 1; }
    }

    char node[64], arch[65], sign[160], raw_host[64];
    resolve_identity(node, sizeof(node), arch, sizeof(arch), sign, sizeof(sign), raw_host, sizeof(raw_host));

    int udp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (udp_sock >= 0) {
        int broadcast = 1;
        setsockopt(udp_sock, SOL_SOCKET, SO_BROADCAST, &broadcast, sizeof(broadcast));
    }

    if (!print_json) {
        printf("[fleet-beacon-c] Starting native telemetry beacon on %s %s (port %d)...\n",
               node, sign, BEACON_PORT);
        fflush(stdout);
    }

    unsigned long long prev_work = 0, prev_total = 0;

    while (1) {
        double cpu_pct = read_cpu(&prev_work, &prev_total);
        double mem_used = 0.0, mem_total = 0.0;
        read_memory(&mem_used, &mem_total);

        char mount[64] = "/";
        double disk_free = 0.0, disk_total = 0.0;
        read_disk(node, mount, sizeof(mount), &disk_free, &disk_total);

        char gpu_str[64];
        read_gpu(gpu_str, sizeof(gpu_str));

        int temp_c = read_temp();
        int bat_pct = read_battery();

        char alert[256] = "";
        if (strcmp(node, "boxC") == 0 && strcmp(mount, "/mnt/kof17") == 0 && disk_free < 3.0) {
            snprintf(alert, sizeof(alert), "kof17 CRITICAL: %.1fG free", disk_free);
        } else if ((strcmp(node, "crostini") == 0 || strcmp(node, "penguin") == 0) && disk_free < 1.0) {
            snprintf(alert, sizeof(alert), "crostini LOW DISK: %.1fG free", disk_free);
        } else if (bat_pct >= 0 && bat_pct <= 15) {
            snprintf(alert, sizeof(alert), "%s BATTERY CRITICAL: %d%%", node, bat_pct);
        }

        char payload[2048];
        snprintf(payload, sizeof(payload),
            "{\"name\":\"%s\",\"hostname\":\"%s\",\"node\":\"%s\",\"arch\":\"%s\",\"sign\":\"%s\","
            "\"timestamp\":%.3f,\"cpu_percent\":%.1f,\"mem_used_gb\":%.1f,\"mem_total_gb\":%.1f,"
            "\"disk_mount\":\"%s\",\"disk_free_gb\":%.1f,\"disk_total_gb\":%.1f,"
            "\"gpu_str\":\"%s\",\"temp_c\":%d,\"battery_percent\":%d,\"alert\":\"%s\"}",
            node, raw_host, node, arch, sign,
            (double)time(NULL), cpu_pct, mem_used, mem_total,
            mount, disk_free, disk_total,
            gpu_str, temp_c, bat_pct, alert);

        /* 1. Broadcast UDP */
        if (udp_sock >= 0) {
            size_t payload_len = strlen(payload);
            for (int i = 0; TARGETS[i] != NULL; ++i) {
                struct sockaddr_in sin;
                memset(&sin, 0, sizeof(sin));
                sin.sin_family = AF_INET;
                sin.sin_port = htons(BEACON_PORT);
                if (inet_pton(AF_INET, TARGETS[i], &sin.sin_addr) > 0) {
                    sendto(udp_sock, payload, payload_len, 0, (struct sockaddr *)&sin, sizeof(sin));
                }
            }
        }

        /* 2. Update local SHM cache */
        update_shm(node, payload);

        /* 3. HTTP WAN Fallback */
        if (strcmp(node, "boxC") != 0) {
            send_wan_http(payload);
        }

        if (print_json) {
            printf("%s\n", payload);
            fflush(stdout);
        }

        if (run_once) {
            break;
        }

        usleep(INTERVAL_US);
    }

    if (udp_sock >= 0) close(udp_sock);
    return 0;
}
