import { UserRound } from 'lucide-react'
import { MotionConfig } from 'motion/react'
import { Button } from '@/components/ui/button'
import { useProfile } from '@/room/profile'
import { useRoom } from '@/room/store'
import { ScreenHeader } from '@/shell/ScreenHeader'
import { Announcer } from './Announcer'
import { Captions } from './Captions'
import { CardStack } from './CardStack'
import { MicButton, MicNotice } from './MicControls'
import { RoomStatus } from './RoomStatus'
import { useCaptions } from './useCaptions'

/** The hero screen: rolling captions on top, jargon cards by the thumb. Nothing scrolls. */
export function LiveScreen() {
  const utterances = useCaptions()
  const knowledge = useRoom((s) => s.knowledge)
  const me = useRoom((s) => s.me)
  const glossaryError = useRoom((s) => s.glossaryError)
  const switchPerson = useProfile((s) => s.switchPerson)

  return (
    <MotionConfig reducedMotion="user">
      <ScreenHeader
        actions={
          <>
            <MicButton />
            <Button
              variant="ghost"
              className="max-w-32 gap-1.5 px-2.5"
              onClick={switchPerson}
              aria-label={`Joined as ${me?.name ?? 'guest'}. Switch person`}
            >
              <UserRound aria-hidden="true" />
              <span className="truncate text-(length:--text-note)">{me?.name}</span>
            </Button>
          </>
        }
      >
        <h1 className="sr-only">Live captions</h1>
        <RoomStatus />
      </ScreenHeader>

      {glossaryError && (
        <p role="alert" className="px-safe pb-2 text-(length:--text-note) font-semibold text-danger">
          The glossary did not load, so cards are paused. Check your connection.
        </p>
      )}

      <Captions
        utterances={utterances}
        knowledge={knowledge}
        meId={me?.user_id}
        emptyHint="Waiting for someone to speak. Captions will roll here."
        className="px-safe"
      />
      <MicNotice />
      <CardStack />
      <Announcer />
    </MotionConfig>
  )
}
