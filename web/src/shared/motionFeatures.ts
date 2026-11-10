// Motion's animation engine, loaded after first paint. `domMax` because CardStack and
// StagePhone use layout animations. Components use the light `m.*` elements; see App.tsx.
import { domMax } from 'motion/react'

export default domMax
