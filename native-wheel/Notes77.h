#ifndef AG_NOTES77_H
#define AG_NOTES77_H
void AGNotesTick(void *env,int variant);
int AGNotesReceive(void *env,void *message,int variant);
int AGNotesInput(int variant,int kind,int a,int b);
int AGNotesSettings(void *env,void *screen,void *graphics,int variant,int action);
void AGNotesInbox(void *env,void *dialog,void *body,int variant);
#endif
