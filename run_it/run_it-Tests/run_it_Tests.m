//
// unit tests for run_it command
//

#import <XCTest/XCTest.h>

#include "Process.h"

@interface run_it_Tests : XCTestCase

@end

@implementation run_it_Tests

- (void)testDescription {
  struct timeval startTime, endTime;
  memset(&startTime, 0, sizeof(startTime));
  memset(&endTime, 0, sizeof(endTime));
  struct timezone unused_tz;
  int status = 0;
  pid_t pid = -1;
  struct rusage rusage;
  memset(&rusage, 0, sizeof(rusage));
  NSArray *args;

  args = @[@"/bin/sleep", @"2"];
  const char *argv[] = {"/bin/sleep", "1", NULL};
  gettimeofday(&startTime, &unused_tz);  // get time before the cmd is run
  XCTAssertTrue(LaunchProcess(argv, &pid));
  XCTAssertTrue(WaitForExit(pid, &status, &rusage));
  gettimeofday(&endTime, &unused_tz);  // time after the command ran
  NSString *description = Description(args, pid, status, startTime, endTime, rusage);
  XCTAssertNotEqual([description rangeOfString:@"cmd=\"/bin/sleep 2\""].location, NSNotFound,
                    "cmd not found in description");
  XCTAssertNotEqual([description rangeOfString:@"status=0"].location, NSNotFound,
                    "status not found in description");
}

- (void)testLaunchAndWait1 {
  int status = 0;
  pid_t pid = -1;
  struct rusage rusage;
  memset(&rusage, 0, sizeof(rusage));

  const char *argv[] = {"/usr/bin/false", NULL};
  XCTAssertTrue(LaunchProcess(argv, &pid));
  XCTAssertTrue(WaitForExit(pid, &status, &rusage));
  XCTAssertNotEqual(status, 0, "status should be non-zero");
}

- (void)testLaunchAndWait2 {
  struct timeval startTime, endTime;
  memset(&startTime, 0, sizeof(startTime));
  memset(&endTime, 0, sizeof(endTime));
  struct timezone unused_tz;
  int status = 0;
  pid_t pid = -1;
  struct rusage rusage;
  memset(&rusage, 0, sizeof(rusage));
  NSArray *args;

  args = @[@"/bin/sleep", @"2"];
  const char *argv[] = {"/bin/sleep", "1", NULL};
  gettimeofday(&startTime, &unused_tz);  // get time before the cmd is run
  XCTAssertTrue(LaunchProcess(argv, &pid));
  XCTAssertTrue(WaitForExit(pid, &status, &rusage));
  gettimeofday(&endTime, &unused_tz);  // time after the command ran
  XCTAssertEqualWithAccuracy(TimevalToDouble(endTime)-TimevalToDouble(startTime), 1, .1,
                             "Sleep time should be about 2");
}

@end
