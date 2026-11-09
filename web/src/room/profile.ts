import { create } from 'zustand'
import { clearIdentity, loadProfile, saveProfile, type Profile } from './identity'

interface ProfileStore {
  profile: Profile | null
  join: (profile: Profile) => void
  /** Leave as this person; the next join starts fresh with a new user id. */
  switchPerson: () => void
}

export const useProfile = create<ProfileStore>((set) => ({
  profile: loadProfile(),
  join: (profile) => {
    saveProfile(profile)
    set({ profile })
  },
  switchPerson: () => {
    clearIdentity()
    set({ profile: null })
  },
}))
