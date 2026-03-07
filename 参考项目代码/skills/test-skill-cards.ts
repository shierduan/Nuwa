#!/usr/bin/env node

import { loadWorkspaceSkillEntries, buildWorkspaceSkillCards, buildWorkspaceSkillCardsByCategory, buildWorkspaceSkillCommandSpecs } from './skills-extract/skills.js';
import path from 'node:path';

async function testSkillCards() {
  console.log('Testing Skill Card Mechanism...\n');
  
  const workspaceDir = path.resolve('.');
  
  // Test loading skill entries with card data
  console.log('1. Loading skill entries...');
  const entries = loadWorkspaceSkillEntries(workspaceDir);
  console.log(`Loaded ${entries.length} skill entries`);
  
  // Find the example skill card
  const exampleSkill = entries.find(entry => entry.skill.name === 'example-skill-card');
  if (exampleSkill) {
    console.log('\n2. Example skill card found:');
    console.log(`   Name: ${exampleSkill.card?.name}`);
    console.log(`   Title: ${exampleSkill.card?.title}`);
    console.log(`   Description: ${exampleSkill.card?.description}`);
    console.log(`   Emoji: ${exampleSkill.card?.emoji}`);
    console.log(`   Category: ${exampleSkill.card?.category}`);
    console.log(`   Tags: ${exampleSkill.card?.tags?.join(', ')}`);
    console.log(`   Color: ${exampleSkill.card?.color}`);
    console.log(`   Background Color: ${exampleSkill.card?.backgroundColor}`);
  } else {
    console.log('\n2. Example skill card not found');
  }
  
  // Test building skill cards
  console.log('\n3. Building skill cards...');
  const cards = buildWorkspaceSkillCards(workspaceDir);
  console.log(`Built ${cards.length} skill cards`);
  
  // Test building skill cards by category
  console.log('\n4. Building skill cards by category...');
  const cardsByCategory = buildWorkspaceSkillCardsByCategory(workspaceDir);
  console.log(`Found ${Object.keys(cardsByCategory).length} categories:`);
  
  Object.entries(cardsByCategory).forEach(([category, categoryCards]) => {
    console.log(`   ${category}: ${categoryCards.length} skills`);
  });
  
  // Test building command specs with card metadata
  console.log('\n5. Building command specs with card metadata...');
  const commandSpecs = buildWorkspaceSkillCommandSpecs(workspaceDir);
  console.log(`Built ${commandSpecs.length} command specs`);
  
  // Find the example command spec
  const exampleCommand = commandSpecs.find(spec => spec.skillName === 'example-skill-card');
  if (exampleCommand) {
    console.log('\n6. Example command spec with card metadata:');
    console.log(`   Command: /${exampleCommand.name}`);
    console.log(`   Skill Name: ${exampleCommand.skillName}`);
    console.log(`   Description: ${exampleCommand.description}`);
    if (exampleCommand.card) {
      console.log(`   Card Title: ${exampleCommand.card.title}`);
      console.log(`   Card Category: ${exampleCommand.card.category}`);
    }
  } else {
    console.log('\n6. Example command spec not found');
  }
  
  console.log('\n✅ Skill card mechanism test completed successfully!');
}

testSkillCards().catch(error => {
  console.error('❌ Skill card mechanism test failed:', error);
  process.exit(1);
});