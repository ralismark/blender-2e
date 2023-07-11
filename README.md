# System Design

This document details the design of the system.

## Goals

- Separate components (known as fragments) that are able to coexists and interoperate, but use a shared base layer.
	- Fragments should not need to know about the existence of other fragments, except in the case of conflicts (e.g. naming conflicts).
	- There should be no need to subvert the base layer - everything addressed by it should provide all necessary functionality without limiting fragments.
- This shared base layer should be independent of any individual fragment.

## Overall Design

A fragment should be a file, with global function calls to register required components.
