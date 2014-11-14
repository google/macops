// fdeadduser
//
// Adds a user from OD to the list of FileVault-enabled users.
// Unlike fdesetup on 10.9+, doesn't require any credentials other than
// those of the user being added. This will probably break in a future
// version of OS X.
//
// Compile with:
//    clang -o fdeadduser{,.m} -framework CoreFoundation -lodfde -lcsfde
//
// Call as:
//    fdeadduser "username" "password"
//
// Returns:
//     0: success
//    -1: bad arguments
//     1: error from ODFDEAddUser

#import <Foundation/Foundation.h>

// Comes from libcsfde
extern CFStringRef CSFDEStorePassphrase(const char* password);

// Comes from libodfde
extern BOOL ODFDEAddUser(
    CFStringRef authuser, CFStringRef authpass, CFStringRef username, CFStringRef password);

int main(int argc, char *argv[]) {
  if (argc < 3) return -1;

  CFStringRef user = CFStringCreateWithCString(NULL, argv[1], kCFStringEncodingUTF8);
  CFStringRef pass = CSFDEStorePassphrase(argv[2]);
  if (!user || !pass) return -1;

  return ODFDEAddUser(user, pass, user, pass) != 1;
}
