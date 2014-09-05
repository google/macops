//
// run_it: run a command and record the resource utilization
//

#include "Process.h"


int main(int argc, const char *argv[]) {
  @autoreleasepool {
    struct timeval startTime, endTime;
    struct timezone unused_tz;
    int status = 0;
    pid_t pid = -1;
    struct rusage rusage;
    memset(&rusage, 0, sizeof(rusage));

    if (argc < 2) {
      fprintf(stderr, "Usage: %s command\n", argv[0]);
      exit(1);
    }

    NSArray *args = [[[NSProcessInfo processInfo] arguments]
                        subarrayWithRange:NSMakeRange(1, argc - 1)];
    gettimeofday(&startTime, &unused_tz);
    if (LaunchProcess(argv + 1, &pid)) {
      if (WaitForExit(pid, &status, &rusage)) {
        gettimeofday(&endTime, &unused_tz);
        NSString *description = Description(args, pid, status, startTime, endTime, rusage);
        syslog(LOG_INFO, "%s", [description UTF8String]);
        return(WEXITSTATUS(status));  // propagate the return value
      }
    }
  }
  return 1;
}
