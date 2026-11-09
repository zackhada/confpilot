import { create } from 'zustand'
import { clearIdentity, loadProfile, saveProfile, type Profile } from './identity'

interface ProfileStore {
  profile: Profile | null
  /** True while the optional "Tune it to me" flow is on screen. Not remembered. */
  tuning: boolean
  join: (profile: Profile, tune?: boolean) => void
  doneTuning: () => void
  /** Leave as this person; the next join starts fresh with a new user id. */
  switchPerson: () => void
}

export const useProfile = create<ProfileStore>((set) => ({
  profile: loadProfile(),
  tuning: false,
  join: (profile, tune = false) => {
    saveProfile(profile)
    set({ profile, tuning: tune })
  },
  doneTuning: () => set({ tuning: false }),
  switchPerson: () => {
    clearIdentity()
    set({ profile: null, tuning: false })
  },
}))
